"""
ThetaGrid — FastAPI Backend
Serves market data, option analytics, and WebSocket feeds.
"""
import asyncio
import json
import math
import random
import pytz
IST = pytz.timezone("Asia/Kolkata")
import time
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import is_configured, BACKEND_PORT
from calculations import (
    calculate_expected_move, calculate_expected_range, calculate_pcr,
    calculate_max_pain, find_oi_support, find_oi_resistance,
    calculate_atm_strike, calculate_straddle_premium,
    calculate_iv_percentile, calculate_oi_change, classify_oi_buildup
)
from smartapi_client import smart_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("thetagrid")

# ---------- In-memory state ----------
market_state: Dict[str, Any] = {}

from persistence import update_persistence
p_data = update_persistence(None, None, None)
market_state["nifty"] = {"prev_close": p_data.get("NIFTY", 24770.0)}
market_state["sensex"] = {"prev_close": p_data.get("SENSEX", 81350.0)}
market_state["vix"] = {"prev_close": p_data.get("VIX", 12.85)}

global_chains = {"NIFTY": [], "SENSEX": []}
import os

def load_straddle_history() -> Dict[str, List[Dict]]:
    hist_file = "straddle_history.json"
    if os.path.exists(hist_file):
        try:
            with open(hist_file, "r") as f:
                data = json.load(f)
                
                # Check if the data is from today, if not clear it
                if data.get("NIFTY") and len(data["NIFTY"]) > 0:
                    first_entry_time = data["NIFTY"][0].get("time")
                    # We assume it resets every day. If it's a new day, we just clear it.
                    # A robust way is checking the date of the file.
                    file_time = datetime.fromtimestamp(os.path.getmtime(hist_file))
                    if file_time.date() != datetime.now(IST).date():
                        return {"NIFTY": [], "SENSEX": []}
                return data
        except Exception as e:
            logger.error(f"Error loading straddle history: {e}")
    return {"NIFTY": [], "SENSEX": []}

straddle_history: Dict[str, List[Dict]] = load_straddle_history()
connected_clients: List[WebSocket] = []
oi_snapshots: Dict[str, List[Dict]] = {"NIFTY": [], "SENSEX": []}

# OI Baseline: stores {token: {"oi": int, "ltp": float}} captured at first tick of the day
# Used for buildup classification (comparing current vs baseline)
oi_baseline: Dict[str, Dict[str, Dict]] = {"NIFTY": {}, "SENSEX": {}}
oi_baseline_date: Optional[str] = None  # Track which date the baseline belongs to

# Straddle premium confirmation filter:
# Instead of hard-rejecting big jumps, we require N consecutive ticks at the new level
# to confirm it's a real move and not a WebSocket glitch.
# Glitches revert in 1-2 ticks; real moves persist.
straddle_filter: Dict[str, Dict] = {
    "NIFTY": {"confirmed": 0, "pending": 0, "pending_count": 0},
    "SENSEX": {"confirmed": 0, "pending": 0, "pending_count": 0},
}
SPIKE_THRESHOLD = {"NIFTY": 50, "SENSEX": 150}  # Points
CONFIRM_TICKS = 3  # Need 3 consecutive ticks at new level to confirm

def get_confirmed_straddle_premium(index: str, new_premium: float) -> float:
    state = straddle_filter[index]
    
    # If first time, just accept
    if state["confirmed"] == 0:
        state["confirmed"] = new_premium
        return new_premium
        
    diff = abs(new_premium - state["confirmed"])
    
    # Normal move, accept immediately
    if diff <= SPIKE_THRESHOLD[index]:
        state["confirmed"] = new_premium
        state["pending"] = 0
        state["pending_count"] = 0
        return new_premium
        
    # Big move detected. Is it the same big move as last tick?
    if abs(new_premium - state["pending"]) < 20: # within 20 points of pending
        state["pending_count"] += 1
        if state["pending_count"] >= CONFIRM_TICKS:
            # Confirmed real move!
            logger.info(f"{index} straddle large move confirmed: {state['confirmed']} -> {new_premium}")
            state["confirmed"] = new_premium
            state["pending"] = 0
            state["pending_count"] = 0
    else:
        # First time seeing this big move, or it changed significantly
        logger.warning(f"{index} straddle spike detected: {new_premium} (prev: {state['confirmed']}). Awaiting confirmation.")
        state["pending"] = new_premium
        state["pending_count"] = 1
        
    return state["confirmed"]




def generate_live_option_chain(index: str, spot_price: float, dte_years: float = 0.0) -> List[Dict]:
    from smartapi_client import smart_client, live_engine
    options = smart_client.get_nearest_expiry_options(index)
    if not options or not spot_price:
        return []

    # Strike interval: NIFTY=50, SENSEX=100
    strike_interval = 50 if index == "NIFTY" else 100
    atm_strike = round(spot_price / strike_interval) * strike_interval
    
    # Filter for ±15 strikes
    min_strike = atm_strike - (15 * strike_interval)
    max_strike = atm_strike + (15 * strike_interval)
    
    # Group by strike
    strikes = {}
    for opt in options:
        try:
            strike = float(opt.get("strike", 0)) / 100.0
            if min_strike <= strike <= max_strike:
                symbol = opt.get("symbol", "")
                if strike not in strikes:
                    strikes[strike] = {"strike": strike, "call_token": "", "put_token": "", "call_oi": 0, "put_oi": 0, "call_ltp": 0, "put_ltp": 0}
                if symbol.endswith("CE"):
                    strikes[strike]["call_token"] = opt["token"]
                elif symbol.endswith("PE"):
                    strikes[strike]["put_token"] = opt["token"]
        except Exception:
            pass

    # Build chain and populate live data
    # Reset baseline if it's a new day
    global oi_baseline_date
    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    if oi_baseline_date != today_str:
        oi_baseline["NIFTY"] = {}
        oi_baseline["SENSEX"] = {}
        oi_baseline_date = today_str

    baseline = oi_baseline.get(index, {})
    has_baseline = len(baseline) > 0

    chain = []
    for strike in sorted(strikes.keys()):
        row = strikes[strike]
        ct = row["call_token"]
        pt = row["put_token"]
        
        row["call_ltp"] = live_engine.live_prices.get(ct, 0)
        row["put_ltp"] = live_engine.live_prices.get(pt, 0)
        row["call_oi"] = live_engine.live_oi.get(ct, 0)
        row["put_oi"] = live_engine.live_oi.get(pt, 0)
        
        if dte_years > 0:
            iv = 0.15 # Approx 15% IV for generic delta
            d1 = (math.log(spot_price / strike) + ((iv**2)/2)*dte_years) / (iv * math.sqrt(dte_years))
            row["call_delta"] = round(norm_cdf(d1), 2)
            row["put_delta"] = round(norm_cdf(d1) - 1.0, 2)
        else:
            row["call_delta"] = 1.0 if spot_price > strike else 0.0
            row["put_delta"] = 0.0 if spot_price > strike else -1.0

        # --- OI Baseline capture (first tick of the day) ---
        if not has_baseline:
            if ct and row["call_oi"] > 0:
                baseline[ct] = {"oi": row["call_oi"], "ltp": row["call_ltp"]}
            if pt and row["put_oi"] > 0:
                baseline[pt] = {"oi": row["put_oi"], "ltp": row["put_ltp"]}

        # --- Buildup classification ---
        if has_baseline:
            # Call side
            cb = baseline.get(ct, {})
            if cb and cb.get("oi", 0) > 0:
                call_oi_chg = row["call_oi"] - cb["oi"]
                call_ltp_chg = row["call_ltp"] - cb["ltp"]
                row["call_oi_change"] = call_oi_chg
                row["call_buildup"] = classify_oi_buildup(call_ltp_chg, call_oi_chg)
            else:
                row["call_oi_change"] = 0
                row["call_buildup"] = "Neutral"

            # Put side
            pb = baseline.get(pt, {})
            if pb and pb.get("oi", 0) > 0:
                put_oi_chg = row["put_oi"] - pb["oi"]
                put_ltp_chg = row["put_ltp"] - pb["ltp"]
                row["put_oi_change"] = put_oi_chg
                row["put_buildup"] = classify_oi_buildup(put_ltp_chg, put_oi_chg)
            else:
                row["put_oi_change"] = 0
                row["put_buildup"] = "Neutral"
        else:
            row["call_oi_change"] = 0
            row["put_oi_change"] = 0
            row["call_buildup"] = "Neutral"
            row["put_buildup"] = "Neutral"

        chain.append(row)

    # Save baseline if this was the first capture
    if not has_baseline and len(baseline) > 0:
        oi_baseline[index] = baseline
        logger.info(f"{index} OI baseline captured: {len(baseline)} tokens")

    return chain

def norm_cdf(x):
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def norm_pdf(x):
    return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)

def get_atm_greeks(spot, iv, dte_years):
    if dte_years <= 0 or iv <= 0:
        return {"delta": 0.5, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    sigma = iv / 100.0
    d1 = (0.5 * sigma**2 * dte_years) / (sigma * math.sqrt(dte_years))
    
    delta = norm_cdf(d1)
    gamma = norm_pdf(d1) / (spot * sigma * math.sqrt(dte_years))
    vega = spot * norm_pdf(d1) * math.sqrt(dte_years) * 0.01
    theta = -(spot * norm_pdf(d1) * sigma) / (2 * math.sqrt(dte_years))
    theta = theta / 365.0
    return {
        "delta": round(delta, 2),
        "gamma": round(gamma, 5),
        "theta": round(theta, 2),
        "vega": round(vega, 2)
    }

def calculate_real_metrics(spot: float, chain: List[Dict], dte: float) -> dict:
    if not chain:
        return {}
    
    total_call_oi = sum(r.get("call_oi", 0) for r in chain)
    total_put_oi = sum(r.get("put_oi", 0) for r in chain)
    pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
    
    max_call_oi = max(chain, key=lambda x: x.get("call_oi", 0))
    max_put_oi = max(chain, key=lambda x: x.get("put_oi", 0))
    oi_resistance = {"strike": max_call_oi["strike"], "oi": max_call_oi.get("call_oi", 0)}
    oi_support = {"strike": max_put_oi["strike"], "oi": max_put_oi.get("put_oi", 0)}
    
    # Max pain
    min_pain = float("inf")
    max_pain_strike = spot
    for strike_cand in [r["strike"] for r in chain]:
        pain = 0
        for r in chain:
            if r["strike"] < strike_cand:
                pain += r.get("call_oi", 0) * (strike_cand - r["strike"])
            if r["strike"] > strike_cand:
                pain += r.get("put_oi", 0) * (r["strike"] - strike_cand)
        if pain < min_pain:
            min_pain = pain
            max_pain_strike = strike_cand
            
    # Approximate IV from straddle premium
    atm = min(chain, key=lambda x: abs(x["strike"] - spot))
    straddle = atm.get("call_ltp", 0) + atm.get("put_ltp", 0)
    
    dte_years = max(1, dte) / 365.0
    # straddle ~ 0.8 * spot * IV * sqrt(DTE)
    atm_iv = 0
    if spot > 0 and dte_years > 0:
        atm_iv = (straddle / (0.8 * spot * math.sqrt(dte_years))) * 100
        
    expected_move = spot * (atm_iv / 100.0) * math.sqrt(dte_years)
    
    # Pseudo IV Percentile based on a typical 10-30 IV range for Indian markets
    ivp = min(100, max(0, int((atm_iv - 10) / (30 - 10) * 100)))
    
    greeks = get_atm_greeks(spot, atm_iv, dte_years)
    
    return {
        "pcr": round(pcr, 2),
        "oi_resistance": oi_resistance,
        "oi_support": oi_support,
        "max_pain": max_pain_strike,
        "atm_iv": round(atm_iv, 2),
        "expected_move": round(expected_move, 2),
        "expected_range": [round(spot - expected_move, 2), round(spot + expected_move, 2)],
        "iv_percentile": ivp,
        "greeks": greeks
    }

# ---------- Scrapers ----------
async def scrape_gift_nifty():
    import httpx
    import re
    while True:
        try:
            async with httpx.AsyncClient() as client:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                resp = await client.get("https://giftnifty.org/", headers=headers, timeout=10)
                if resp.status_code == 200:
                    html = resp.text
                    
                    # Look for the Gift Nifty tape item with current structure:
                    # <a class="gn-tape-i" href="https://giftnifty.org/">
                    #   <span class="gn-tape-n">Gift Nifty</span>
                    #   <span class="gn-mono">25,358.50</span>
                    #   <span class="gn-mono up">+0.18%</span>
                    # </a>
                    
                    # First try to find the Gift Nifty tape item
                    # Note: Website uses Unicode minus (U+2212) instead of hyphen
                    gift_pattern = r'<a class="gn-tape-i"[^>]*href="https://giftnifty\.org/"[^>]*>.*?<span class="gn-tape-n">Gift Nifty</span>\s*<span class="gn-mono">([\d,\.]+)</span>\s*<span class="gn-mono (\w+)">([+\-−]?\d+\.\d+)%</span>'
                    match = re.search(gift_pattern, html, re.DOTALL)
                    
                    if match:
                        price_str = match.group(1).replace(",", "")
                        change_type = match.group(2)  # "up" or "down" for class
                        change_str = match.group(3).replace("−", "-")  # Replace Unicode minus with regular minus
                        change_pct = float(change_str)
                        
                        price = float(price_str)
                        
                        if "gift_nifty" not in market_state:
                            market_state["gift_nifty"] = {"value": price, "change": 0, "points_change": 0}
                            
                        market_state["gift_nifty"]["value"] = price
                        market_state["gift_nifty"]["change"] = change_pct
                        
                        # For points change, we need to calculate from previous value
                        if "value" in market_state["gift_nifty"]:
                            old_value = market_state["gift_nifty"].get("old_value", price)
                            points_change = price - old_value
                            market_state["gift_nifty"]["points_change"] = round(points_change, 2)
                            market_state["gift_nifty"]["old_value"] = price
                            
                        logger.info(f"Scraped GIFT Nifty: {price}, change: {change_pct}%")
                    else:
                        # Fallback to older patterns if new one fails
                        price_match = re.search(r"font-number\"\>([\d,]+)\.\<small\>([\d]+)", html)
                        if not price_match:
                            price_match = re.search(r"font-number\"\>([\d,\.]+)\<", html)
                            
                        change_match = re.search(r"class=\"fa fa-arrow-circle-(down|up) ipercent\"\>\</i\>([\-\+\d\.]+)%", html)
                        points_match = re.search(r"ipercent\"\>\</i\>([\-\+\d\.]+)%\s+&nbsp;&nbsp;&nbsp;\<i class=\"fa fa-arrow-circle-(down|up) ipercent\"\>\</i\>([\-\+\d\.]+)\<", html)
                        
                        if price_match:
                            p_str = price_match.group(1).replace(",", "")
                            if len(price_match.groups()) > 1 and price_match.group(2):
                                p_str += "." + price_match.group(2)
                            
                            price = float(p_str)
                            if "gift_nifty" not in market_state:
                                market_state["gift_nifty"] = {"value": price, "change": 0, "points_change": 0}
                                
                            market_state["gift_nifty"]["value"] = price
                            
                            if change_match:
                                market_state["gift_nifty"]["change"] = float(change_match.group(2))
                                
                            if points_match:
                                market_state["gift_nifty"]["points_change"] = float(points_match.group(3))
                        else:
                            logger.warning("Could not find Gift Nifty data in HTML")
        except Exception as e:
            logger.error(f"Failed to scrape GIFT Nifty: {e}")
            
        await asyncio.sleep(15)

# ---------- Lifespan ----------
async def broadcast_loop():
    """Periodically broadcast market data to all connected WebSocket clients."""
    while True:
        try:
            if is_configured() and smart_client.authenticated:
                from smartapi_client import live_engine, smart_client as sc
                
                # Self-healing WebSocket check (handles both explicit disconnects and silent drops)
                time_since_tick = time.time() - getattr(live_engine, "last_tick_time", time.time())
                is_stuck = time_since_tick > 30
                
                if not live_engine.is_connected or is_stuck:
                    if not hasattr(live_engine, "disconnected_ticks"):
                        live_engine.disconnected_ticks = 0
                    live_engine.disconnected_ticks += 1
                    
                    if live_engine.disconnected_ticks > 15:
                        logger.warning(f"Live WebSocket unhealthy for 15s (connected: {live_engine.is_connected}, stale: {is_stuck}). Running self-healing re-auth...")
                        try:
                            if live_engine.ws:
                                live_engine.ws.close()
                        except:
                            pass
                        
                        if await smart_client.authenticate():
                            live_engine.start()
                        live_engine.disconnected_ticks = 0
                else:
                    live_engine.disconnected_ticks = 0

                data = {
                    "timestamp": datetime.now(IST).strftime("%H:%M:%S"),
                    "demo_mode": False,
                    "nifty": {"prev_close": market_state["nifty"]["prev_close"]},
                    "sensex": {"prev_close": market_state["sensex"]["prev_close"]},
                    "vix": {"prev_close": market_state["vix"]["prev_close"]},
                    "gift_nifty": market_state.get("gift_nifty", {})
                }
                
                # NIFTY Live
                live_nifty = live_engine.live_prices.get("99926000")
                if not live_nifty and data["nifty"]["prev_close"]:
                    live_nifty = data["nifty"]["prev_close"]
                    
                if live_nifty:
                    # Clear data to prevent dummy values from leaking to UI
                    data["nifty"]["straddle_premium"] = 0
                    
                    data["nifty"]["spot"] = live_nifty
                    data["nifty"]["points_change"] = round(live_nifty - data["nifty"]["prev_close"], 2)
                    data["nifty"]["change"] = round((data["nifty"]["points_change"] / data["nifty"]["prev_close"]) * 100, 2)
                    data["nifty"]["dte"] = sc.get_dte("NIFTY")
                    dte_years_nifty = max(1, data["nifty"]["dte"]) / 365.0
                    
                    # Generate Chain
                    live_chain = generate_live_option_chain("NIFTY", live_nifty, dte_years_nifty)
                    if live_chain:
                        global_chains["NIFTY"] = live_chain
                        # 1. Base ATM on Spot
                        base_atm = round(live_nifty / 50) * 50
                        base_atm_row = next((r for r in live_chain if r["strike"] == base_atm), None)
                        
                        synthetic_future = live_nifty
                        if base_atm_row:
                            c_ltp = base_atm_row.get("call_ltp", 0)
                            p_ltp = base_atm_row.get("put_ltp", 0)
                            if c_ltp > 0 and p_ltp > 0:
                                syn = base_atm + c_ltp - p_ltp
                                if abs(syn - live_nifty) < 200:  # Protect against exchange LTP glitches
                                    synthetic_future = syn
                            
                        # 2. True ATM based on Synthetic Future
                        true_atm = round(synthetic_future / 50) * 50
                        data["nifty"]["atm_strike"] = true_atm
                        data["nifty"]["synthetic_future"] = round(synthetic_future, 2)
                        
                        # Straddle premium at True ATM
                        true_atm_row = next((r for r in live_chain if r["strike"] == true_atm), None)
                        if true_atm_row:
                            new_premium = true_atm_row.get("call_ltp", 0) + true_atm_row.get("put_ltp", 0)
                            data["nifty"]["straddle_premium"] = get_confirmed_straddle_premium("NIFTY", new_premium)
                            data["_nifty_live_premium"] = True  # Flag: this premium is from live data
                            
                        # Override key levels with REAL metrics
                        real_metrics = calculate_real_metrics(live_nifty, live_chain, data["nifty"]["dte"])
                        data["nifty"].update(real_metrics)


                # SENSEX Live
                live_sensex = live_engine.live_prices.get("99919000")
                if not live_sensex and data["sensex"]["prev_close"]:
                    live_sensex = data["sensex"]["prev_close"]
                    
                if live_sensex:
                    # Clear data to prevent dummy values from leaking to UI
                    data["sensex"]["straddle_premium"] = 0
                    
                    data["sensex"]["spot"] = live_sensex
                    data["sensex"]["points_change"] = round(live_sensex - data["sensex"]["prev_close"], 2)
                    data["sensex"]["change"] = round((data["sensex"]["points_change"] / data["sensex"]["prev_close"]) * 100, 2)
                    data["sensex"]["dte"] = sc.get_dte("SENSEX")
                    dte_years_sensex = max(1, data["sensex"]["dte"]) / 365.0
                    
                    # Generate Chain
                    live_chain_s = generate_live_option_chain("SENSEX", live_sensex, dte_years_sensex)
                    if live_chain_s:
                        global_chains["SENSEX"] = live_chain_s
                        base_atm_s = round(live_sensex / 100) * 100
                        base_atm_row_s = next((r for r in live_chain_s if r["strike"] == base_atm_s), None)
                        
                        synthetic_future_s = live_sensex
                        if base_atm_row_s:
                            c_ltp_s = base_atm_row_s.get("call_ltp", 0)
                            p_ltp_s = base_atm_row_s.get("put_ltp", 0)
                            if c_ltp_s > 0 and p_ltp_s > 0:
                                syn_s = base_atm_s + c_ltp_s - p_ltp_s
                                if abs(syn_s - live_sensex) < 600:
                                    synthetic_future_s = syn_s
                            
                        true_atm_s = round(synthetic_future_s / 100) * 100
                        data["sensex"]["atm_strike"] = true_atm_s
                        data["sensex"]["synthetic_future"] = round(synthetic_future_s, 2)
                        
                        true_atm_row_s = next((r for r in live_chain_s if r["strike"] == true_atm_s), None)
                        if true_atm_row_s:
                            new_premium_s = true_atm_row_s.get("call_ltp", 0) + true_atm_row_s.get("put_ltp", 0)
                            data["sensex"]["straddle_premium"] = get_confirmed_straddle_premium("SENSEX", new_premium_s)
                            data["_sensex_live_premium"] = True  # Flag: this premium is from live data

                        # Override key levels with REAL metrics
                        real_metrics_s = calculate_real_metrics(live_sensex, live_chain_s, data["sensex"]["dte"])
                        data["sensex"].update(real_metrics_s)

                # INDIA VIX Live
                live_vix = live_engine.live_prices.get("99926017")
                if not live_vix and data["vix"]["prev_close"]:
                    live_vix = data["vix"]["prev_close"]
                    
                if live_vix:
                    data["vix"]["value"] = live_vix
                    data["vix"]["points_change"] = round(live_vix - data["vix"]["prev_close"], 2)
                    data["vix"]["change"] = round((data["vix"]["points_change"] / data["vix"]["prev_close"]) * 100, 2) if data["vix"]["prev_close"] else 0
                
                # GIFT Nifty Live (from scraper)
                if "gift_nifty" in market_state:
                    gn = market_state["gift_nifty"]
                    if "value" in gn and "nifty" in data and "spot" in data["nifty"]:
                        premium = gn["value"] - data["nifty"]["spot"]
                        gn["premium"] = round(premium, 2)
                        gn["premium_percent"] = round((premium / data["nifty"]["spot"]) * 100, 2)
                    data["gift_nifty"] = gn
                            
            else:
                data = mock_engine.tick(is_live=False)

            market_state.update(data)
            
            now = datetime.now(IST)
            
            # Periodically update persistence store
            if now.second % 15 == 0:
                from persistence import update_persistence
                nifty_spot = data["nifty"].get("spot")
                sensex_spot = data["sensex"].get("spot")
                vix_val = data["vix"].get("value")
                
                if nifty_spot and sensex_spot and vix_val:
                    new_prev = update_persistence(nifty_spot, sensex_spot, vix_val)
                    if new_prev:
                        market_state["nifty"]["prev_close"] = new_prev.get("NIFTY", market_state["nifty"]["prev_close"])
                        market_state["sensex"]["prev_close"] = new_prev.get("SENSEX", market_state["sensex"]["prev_close"])
                        market_state["vix"]["prev_close"] = new_prev.get("VIX", market_state["vix"]["prev_close"])

            # Append straddle history
            now = datetime.now(IST)
            now_str = now.strftime("%H:%M:%S")
            
            # Reset history at 9:15 AM (start of trading day)
            if now.hour == 9 and now.minute == 15 and now.second < 2:
                straddle_history["NIFTY"].clear()
                straddle_history["SENSEX"].clear()
            for idx in ["NIFTY", "SENSEX"]:
                idx_lower = idx.lower()
                
                # TEMPORARILY DISABLED for weekend testing: ONLY record history if this premium came from live data
                if not data.get(f"_{idx_lower}_live_premium"):
                    continue
                
                # Only record history during market hours, stopping at 15:40
                is_after_market = (now.hour > 15) or (now.hour == 15 and now.minute >= 40)
                
                premium = data[idx_lower]["straddle_premium"]
                
                if not is_after_market:
                    # Hard cap: reject obviously glitched values
                    max_sane = 600 if idx == "NIFTY" else 1600
                    if premium > max_sane or premium <= 0:
                        continue
                    
                    if len(straddle_history[idx]) == 0 or (now - datetime.strptime(straddle_history[idx][-1]["time"], "%H:%M:%S").replace(year=now.year, month=now.month, day=now.day)).total_seconds() >= 60:
                        # Calculate VWAP proxy (Cumulative Average)
                        current_count = len(straddle_history[idx])
                        if current_count > 0:
                            prev_vwap = straddle_history[idx][-1].get("vwap", straddle_history[idx][-1]["premium"])
                            vwap = prev_vwap + (premium - prev_vwap) / (current_count + 1)
                        else:
                            vwap = premium

                        straddle_history[idx].append({
                            "time": now_str,
                            "premium": premium,
                            "vwap": round(vwap, 2)
                        })

                # Attach latest VWAP to live tick data
                if len(straddle_history[idx]) > 0:
                    data[idx_lower]["vwap"] = straddle_history[idx][-1].get("vwap", premium)

            # Save straddle history to disk periodically
            if now.second % 15 == 0:
                try:
                    with open("straddle_history.json", "w") as f:
                        json.dump(straddle_history, f)
                except Exception as e:
                    logger.error(f"Error saving straddle history: {e}")

            # Broadcast to connected clients
            payload = json.dumps(data)
            disconnected = []
            for ws in connected_clients:
                try:
                    await ws.send_text(payload)
                except Exception:
                    disconnected.append(ws)
            for ws in disconnected:
                connected_clients.remove(ws)

        except Exception as e:
            logger.error(f"Broadcast error: {e}")

        await asyncio.sleep(1)  # 1 second tick


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan: start background tasks."""
    logger.info("=" * 50)
    logger.info("  ThetaGrid Backend Starting...")
    logger.info("=" * 50)

    if is_configured():
        logger.info("Angel One credentials found. Authenticating...")
        if await smart_client.authenticate():
            await smart_client.load_instrument_master()
            from smartapi_client import live_engine
            
            def subscribe_all():
                logger.info("Subscribing to live tokens...")
                # Subscribe to indices (Mode 1 for LTP)
                live_engine.subscribe(1, ["99926000", "99926017"], mode=1)
                # Exchange Type 9 (NSE Indices)
                live_engine.subscribe(9, ["26000", "26017"], mode=1)
                # Exchange Type 3 (BSE) for SENSEX
                live_engine.subscribe(3, ["99919000", "19000"], mode=1)
                
                # Helper to chunk list
                def chunk_list(lst, n):
                    for i in range(0, len(lst), n):
                        yield lst[i:i + n]
                
                # Subscribe to NIFTY Options (Exchange Type 2: NFO)
                nifty_opts = smart_client.get_nearest_expiry_options("NIFTY")
                nfo_tokens = [opt["token"] for opt in nifty_opts]
                if nfo_tokens:
                    for chunk in chunk_list(nfo_tokens, 50):
                        live_engine.subscribe(2, chunk, mode=3)
                        time.sleep(0.1) # sync sleep since we might be in thread
                    
                # Subscribe to SENSEX Options (Exchange Type 4: BFO/BSE_FO)
                sensex_opts = smart_client.get_nearest_expiry_options("SENSEX")
                bfo_tokens = [opt["token"] for opt in sensex_opts]
                if bfo_tokens:
                    for chunk in chunk_list(bfo_tokens, 50):
                        live_engine.subscribe(4, chunk, mode=3)
                        time.sleep(0.1)
                        
            live_engine.on_connect = subscribe_all
            live_engine.start()
                
    else:
        logger.info("No credentials configured. To use live data, configure .env with your Angel One SmartAPI credentials.")

    # Start background loops
    broadcast_task = asyncio.create_task(broadcast_loop())
    gift_task = asyncio.create_task(scrape_gift_nifty())
    
    yield
    
    # Cleanup
    broadcast_task.cancel()
    gift_task.cancel()


# ---------- FastAPI App ----------
app = FastAPI(
    title="ThetaGrid API",
    description="Options Selling Intelligence Dashboard Backend",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- REST Endpoints ----------
@app.get("/api/status")
async def get_status():
    """Health check and mode info."""
    return {
        "status": "ok",
        "mode": "live" if (is_configured() and smart_client.authenticated) else "demo",
        "is_configured": is_configured(),
        "timestamp": datetime.now(IST).isoformat(),
    }

class BrokerLoginRequest(BaseModel):
    broker: str
    api_key: str
    client_id: str
    password: str
    totp_secret: str

@app.post("/api/broker/login")
async def broker_login(req: BrokerLoginRequest):
    """Save broker credentials to .env and trigger a reload."""
    if req.broker.lower() != "angelone":
        raise HTTPException(status_code=400, detail="Currently only Angel One is supported.")
        
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    
    # Read existing
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            env_lines = f.readlines()
            
    new_env = {}
    for line in env_lines:
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            new_env[k.strip()] = v.strip()
            
    new_env["ANGEL_API_KEY"] = req.api_key
    new_env["ANGEL_CLIENT_ID"] = req.client_id
    new_env["ANGEL_PASSWORD"] = req.password
    new_env["ANGEL_TOTP_SECRET"] = req.totp_secret
    
    # Write back
    with open(env_path, "w") as f:
        f.write("# Angel One SmartAPI Credentials\n")
        f.write(f"ANGEL_API_KEY={req.api_key}\n")
        f.write(f"ANGEL_CLIENT_ID={req.client_id}\n")
        f.write(f"ANGEL_PASSWORD={req.password}\n")
        f.write(f"ANGEL_TOTP_SECRET={req.totp_secret}\n")
        f.write("\n# Server Config\n")
        f.write(f"BACKEND_PORT={new_env.get('BACKEND_PORT', '8000')}\n")
        f.write(f"FRONTEND_PORT={new_env.get('FRONTEND_PORT', '5173')}\n")
        
    return {"status": "success", "message": "Credentials saved! Backend is reloading..."}

@app.post("/api/broker/logout")
async def broker_logout():
    """Clear broker credentials from .env and trigger a reload."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    
    # Read existing
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            env_lines = f.readlines()
            
    new_env = {}
    for line in env_lines:
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            new_env[k.strip()] = v.strip()
            
    # Write back without Angel One credentials
    with open(env_path, "w") as f:
        f.write("# Angel One SmartAPI Credentials\n")
        f.write("ANGEL_API_KEY=\n")
        f.write("ANGEL_CLIENT_ID=\n")
        f.write("ANGEL_PASSWORD=\n")
        f.write("ANGEL_TOTP_SECRET=\n")
        f.write("\n# Server Config\n")
        f.write(f"BACKEND_PORT={new_env.get('BACKEND_PORT', '8000')}\n")
        f.write(f"FRONTEND_PORT={new_env.get('FRONTEND_PORT', '5173')}\n")
        
    return {"status": "success", "message": "Logged out successfully! Backend is reloading..."}


@app.get("/api/debug-live-prices")
async def debug_prices():
    from smartapi_client import live_engine
    return {"prices": live_engine.live_prices, "oi": len(live_engine.live_oi)}

@app.get("/api/market")
async def get_market_data():
    """Get current market snapshot."""
    return market_state


@app.get("/api/option-chain/{index}")
async def get_option_chain(index: str = "NIFTY"):
    """Get option chain for an index."""
    index = index.upper()
    if index not in ("NIFTY", "SENSEX"):
        return {"error": "Index must be NIFTY or SENSEX"}
    return {
        "index": index,
        "chain": global_chains.get(index, []),
        "timestamp": datetime.now(IST).isoformat(),
    }


@app.get("/api/buildup/{index}")
async def get_buildup_summary(index: str = "NIFTY"):
    """Get aggregate OI buildup summary for an index."""
    index = index.upper()
    if index not in ("NIFTY", "SENSEX"):
        return {"error": "Index must be NIFTY or SENSEX"}
    
    chain = global_chains.get(index, [])
    
    # Count buildup types across all strikes
    call_counts = {"Long Buildup": 0, "Short Buildup": 0, "Long Unwinding": 0, "Short Covering": 0, "Neutral": 0}
    put_counts = {"Long Buildup": 0, "Short Buildup": 0, "Long Unwinding": 0, "Short Covering": 0, "Neutral": 0}
    
    total_call_oi_change = 0
    total_put_oi_change = 0
    
    # Top movers: strikes with highest absolute OI change
    call_movers = []
    put_movers = []
    
    idx_lower = index.lower()
    atm_strike = market_state.get(idx_lower, {}).get("atm_strike")

    for row in chain:
        strike = row["strike"]
        cb = row.get("call_buildup", "Neutral")
        pb = row.get("put_buildup", "Neutral")
        
        c_oi_chg = row.get("call_oi_change", 0)
        p_oi_chg = row.get("put_oi_change", 0)
        
        # Option Seller Optimization: Only count OTM strikes for sentiment/counts
        # For Calls, OTM is strike > ATM. For Puts, OTM is strike < ATM.
        is_call_otm = atm_strike and strike > atm_strike
        is_put_otm = atm_strike and strike < atm_strike
        
        # If ATM is unknown, just count everything
        if not atm_strike or is_call_otm:
            call_counts[cb] = call_counts.get(cb, 0) + 1
            total_call_oi_change += c_oi_chg  # Accumulate all OTM OI
        
        if not atm_strike or is_put_otm:
            put_counts[pb] = put_counts.get(pb, 0) + 1
            total_put_oi_change += p_oi_chg   # Accumulate all OTM OI
        
        if abs(c_oi_chg) > 0:
            call_movers.append({"strike": row["strike"], "oi_change": c_oi_chg, "buildup": cb})
        if abs(p_oi_chg) > 0:
            put_movers.append({"strike": row["strike"], "oi_change": p_oi_chg, "buildup": pb})
    
    # Sort by absolute OI change, take top 5
    call_movers.sort(key=lambda x: abs(x["oi_change"]), reverse=True)
    put_movers.sort(key=lambda x: abs(x["oi_change"]), reverse=True)
    
    # Determine dominant sentiment
    # Calls: Short Buildup = bearish (writers selling), Long Buildup = bullish
    # Puts: Long Buildup = bearish (put buying), Short Buildup = bullish (put writing)
    call_bearish = call_counts["Short Buildup"] + call_counts["Long Unwinding"]
    call_bullish = call_counts["Long Buildup"] + call_counts["Short Covering"]
    put_bearish = put_counts["Long Buildup"] + put_counts["Short Covering"]
    put_bullish = put_counts["Short Buildup"] + put_counts["Long Unwinding"]
    
    if (call_bullish + put_bullish) > (call_bearish + put_bearish):
        sentiment = "Bullish"
    elif (call_bearish + put_bearish) > (call_bullish + put_bullish):
        sentiment = "Bearish"
    else:
        sentiment = "Neutral"
    
    has_baseline = len(oi_baseline.get(index, {})) > 0
    
    return {
        "index": index,
        "has_baseline": has_baseline,
        "sentiment": sentiment,
        "total_call_oi_change": total_call_oi_change,
        "total_put_oi_change": total_put_oi_change,
        "call_counts": call_counts,
        "put_counts": put_counts,
        "top_call_movers": call_movers[:5],
        "top_put_movers": put_movers[:5],
        "timestamp": datetime.now(IST).isoformat(),
    }


@app.get("/api/straddle-history/{index}")
async def get_straddle_history(index: str = "NIFTY"):
    """Get ATM straddle premium history for charting."""
    index = index.upper()
    if index not in ("NIFTY", "SENSEX"):
        return {"error": "Index must be NIFTY or SENSEX"}
    
    # Filter out any outliers that may have slipped through
    max_sane = 600 if index == "NIFTY" else 1600
    raw = straddle_history.get(index, [])
    filtered = [p for p in raw if 0 < p.get("premium", 0) <= max_sane]
    
    return {
        "index": index,
        "history": filtered,
    }


# ---------- WebSocket ----------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time market data WebSocket."""
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info(f"WebSocket client connected. Total: {len(connected_clients)}")
    try:
        while True:
            # Keep connection alive, listen for client messages
            data = await websocket.receive_text()
            # Client can send commands like {"action": "subscribe", "index": "NIFTY"}
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(connected_clients)}")


# ---------- Entry point ----------
_positions_cache = None
_last_positions_fetch = 0

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=BACKEND_PORT, reload=True)

@app.get("/api/positions")
async def get_positions():
    """Fetch active positions from Angel One."""
    if not smart_client.authenticated or not smart_client.smart_api:
        return {"status": "error", "message": "Not authenticated", "data": []}
        
    global _positions_cache, _last_positions_fetch
    now = time.time()
    if _positions_cache is not None and (now - _last_positions_fetch) < 3:
        return {"status": "success", "data": _positions_cache, "cached": True}
        
    try:
        positions_response = smart_client.smart_api.position()
        
        # Auto-reauth if token is invalid
        if positions_response and (positions_response.get("errorCode") == "AG8001" or positions_response.get("message") == "Invalid Token"):
            logger.warning("Angel One token expired (AG8001). Attempting auto-reauthentication...")
            auth_success = await smart_client.authenticate()
            if auth_success:
                positions_response = smart_client.smart_api.position()
                
                # Restart websocket with new feed token
                from smartapi_client import live_engine
                logger.info("Restarting Live WebSocket after re-auth...")
                try:
                    if live_engine.ws:
                        live_engine.ws.close()
                except:
                    pass
                live_engine.start()
                
        if positions_response and (positions_response.get("status") or positions_response.get("success")):
            _positions_cache = positions_response.get("data", [])
            _last_positions_fetch = time.time()
            return {"status": "success", "data": _positions_cache, "cached": False}
        else:
            msg = positions_response.get("message", "Unknown error") if positions_response else "Empty response"
            return {"status": "error", "message": msg, "data": []}
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        return {"status": "error", "message": str(e), "data": []}
