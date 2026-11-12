"""
ThetaGrid — Calculation Engine
Computes max pain, expected move, PCR, and other derivatives from raw market data.
"""
import math
from typing import Dict, List, Optional, Tuple


def calculate_expected_move(spot: float, iv: float, dte: int) -> float:
    """
    Calculate 1-sigma expected move.
    Formula: Spot × (IV/100) × √(DTE/365)
    """
    if dte <= 0 or iv <= 0:
        return 0.0
    return spot * (iv / 100.0) * math.sqrt(dte / 365.0)


def calculate_expected_range(spot: float, iv: float, dte: int) -> Tuple[float, float]:
    """Return (lower, upper) expected range based on 1σ move."""
    move = calculate_expected_move(spot, iv, dte)
    return (round(spot - move, 2), round(spot + move, 2))


def calculate_pcr(option_chain: List[Dict]) -> float:
    """
    Calculate Put-Call Ratio based on Open Interest.
    PCR = Total Put OI / Total Call OI
    """
    total_put_oi = sum(item.get("put_oi", 0) for item in option_chain)
    total_call_oi = sum(item.get("call_oi", 0) for item in option_chain)
    if total_call_oi == 0:
        return 0.0
    return round(total_put_oi / total_call_oi, 3)


def calculate_max_pain(option_chain: List[Dict]) -> float:
    """
    Calculate max pain strike — the strike price at which total losses
    for option buyers (both CE and PE) are maximized.
    """
    if not option_chain:
        return 0.0

    strikes = [item["strike"] for item in option_chain]
    min_pain = float("inf")
    max_pain_strike = strikes[0] if strikes else 0

    for test_strike in strikes:
        total_pain = 0.0
        for item in option_chain:
            strike = item["strike"]
            call_oi = item.get("call_oi", 0)
            put_oi = item.get("put_oi", 0)

            # Call buyer pain: max(0, strike - test_strike) × call_oi
            if strike < test_strike:
                total_pain += (test_strike - strike) * call_oi

            # Put buyer pain: max(0, test_strike - strike) × put_oi
            if strike > test_strike:
                total_pain += (strike - test_strike) * put_oi

        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = test_strike

    return max_pain_strike


def find_oi_support(option_chain: List[Dict]) -> Dict:
    """Find highest Put OI strike (OI Support level)."""
    if not option_chain:
        return {"strike": 0, "oi": 0}
    max_put = max(option_chain, key=lambda x: x.get("put_oi", 0))
    return {"strike": max_put["strike"], "oi": max_put.get("put_oi", 0)}


def find_oi_resistance(option_chain: List[Dict]) -> Dict:
    """Find highest Call OI strike (OI Resistance level)."""
    if not option_chain:
        return {"strike": 0, "oi": 0}
    max_call = max(option_chain, key=lambda x: x.get("call_oi", 0))
    return {"strike": max_call["strike"], "oi": max_call.get("call_oi", 0)}


def calculate_atm_strike(spot: float, strike_gap: int) -> int:
    """Round spot to nearest strike price."""
    return int(round(spot / strike_gap) * strike_gap)


def calculate_straddle_premium(atm_ce_ltp: float, atm_pe_ltp: float) -> float:
    """ATM Straddle premium = CE LTP + PE LTP."""
    return round(atm_ce_ltp + atm_pe_ltp, 2)


def calculate_iv_percentile(current_iv: float, historical_ivs: List[float]) -> float:
    """
    IV Percentile = % of days in the lookback period where IV was below current IV.
    """
    if not historical_ivs:
        return 50.0
    count_below = sum(1 for iv in historical_ivs if iv < current_iv)
    return round((count_below / len(historical_ivs)) * 100, 1)


def calculate_oi_change(current_oi: int, previous_oi: int) -> int:
    """Calculate change in OI from previous snapshot."""
    return current_oi - previous_oi


def classify_oi_buildup(price_change: float, oi_change: int) -> str:
    """
    Classify OI buildup based on price and OI change:
    - Long Buildup: Price ↑, OI ↑
    - Short Buildup: Price ↓, OI ↑
    - Long Unwinding: Price ↓, OI ↓
    - Short Covering: Price ↑, OI ↓
    """
    if price_change > 0 and oi_change > 0:
        return "Long Buildup"
    elif price_change < 0 and oi_change > 0:
        return "Short Buildup"
    elif price_change < 0 and oi_change < 0:
        return "Long Unwinding"
    elif price_change > 0 and oi_change < 0:
        return "Short Covering"
    return "Neutral"
