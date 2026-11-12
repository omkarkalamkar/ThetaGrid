"""
ThetaGrid — Angel One SmartAPI Client Wrapper
Handles authentication, instrument master parsing, market data fetching,
and option chain construction.
"""
import json
import time
import math
import logging
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from config import (
    ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_PASSWORD, ANGEL_TOTP_SECRET,
    NIFTY_TOKEN, SENSEX_TOKEN, VIX_TOKEN, GIFT_NIFTY_TOKEN,
    NIFTY_STRIKE_GAP, SENSEX_STRIKE_GAP, STRIKES_RANGE,
    is_configured
)

logger = logging.getLogger("thetagrid.smartapi")

# Instrument master URL
INSTRUMENT_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

# API base
API_BASE = "https://apiconnect.angelone.in"


class SmartAPIClient:
    """Wrapper around Angel One SmartAPI for ThetaGrid."""

    def __init__(self):
        self.api_key = ANGEL_API_KEY
        self.client_id = ANGEL_CLIENT_ID
        self.password = ANGEL_PASSWORD
        self.totp_secret = ANGEL_TOTP_SECRET
        self.jwt_token = None
        self.feed_token = None
        self.refresh_token = None
        self.smart_api = None
        self.instruments: Dict[str, Any] = {}
        self.nifty_options: List[Dict] = []
        self.sensex_options: List[Dict] = []
        self.authenticated = False

    async def authenticate(self) -> bool:
        """Authenticate with Angel One SmartAPI using TOTP."""
        if not is_configured():
            logger.warning("SmartAPI credentials not configured. Running in demo mode.")
            return False

        try:
            import pyotp
            from SmartApi import SmartConnect

            self.smart_api = SmartConnect(api_key=self.api_key)
            totp = pyotp.TOTP(self.totp_secret).now()

            data = self.smart_api.generateSession(self.client_id, self.password, totp)

            if data.get("status"):
                self.jwt_token = data["data"]["jwtToken"]
                self.feed_token = self.smart_api.getfeedToken()
                self.refresh_token = data["data"].get("refreshToken", "")
                self.authenticated = True
                logger.info("SmartAPI authentication successful")
                return True
            else:
                logger.error(f"SmartAPI auth failed: {data.get('message', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"SmartAPI auth exception: {e}")
            return False

    async def load_instrument_master(self):
        """Download and parse the instrument master file."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(INSTRUMENT_MASTER_URL)
                if resp.status_code == 200:
                    all_instruments = resp.json()

                    # Filter NIFTY options (NFO, OPTIDX)
                    self.nifty_options = [
                        inst for inst in all_instruments
                        if inst.get("name") == "NIFTY" and
                        inst.get("instrumenttype") in ("OPTIDX",) and
                        inst.get("exch_seg") == "NFO"
                    ]

                    # Filter SENSEX options (BFO, OPTIDX)
                    self.sensex_options = [
                        inst for inst in all_instruments
                        if inst.get("name") == "SENSEX" and
                        inst.get("instrumenttype") in ("OPTIDX",) and
                        inst.get("exch_seg") == "BFO"
                    ]

                    logger.info(
                        f"Loaded instruments: {len(self.nifty_options)} NIFTY options, "
                        f"{len(self.sensex_options)} SENSEX options"
                    )
                    return True
        except Exception as e:
            logger.error(f"Failed to load instrument master: {e}")
        return False

    def get_nearest_expiry_options(self, index: str = "NIFTY") -> List[Dict]:
        """Get options for the nearest expiry."""
        options = self.nifty_options if index == "NIFTY" else self.sensex_options
        if not options:
            return []

        # Parse expiry dates and find nearest
        today = datetime.now().date()
        dated_options = []
        for opt in options:
            try:
                exp_str = opt.get("expiry", "")
                exp_date = datetime.strptime(exp_str, "%d%b%Y").date()
                opt["_expiry_date"] = exp_date
                dated_options.append(opt)
            except (ValueError, TypeError):
                continue

        if not dated_options:
            return []

        # Find expirations >= today
        future_opts = [opt for opt in dated_options if opt["_expiry_date"] >= today]
        
        if future_opts:
            nearest_expiry = min(future_opts, key=lambda x: x["_expiry_date"])["_expiry_date"]
            return [opt for opt in future_opts if opt["_expiry_date"] == nearest_expiry]
        else:
            # Fallback if system clock is way ahead of data
            max_expiry = max(dated_options, key=lambda x: x["_expiry_date"])["_expiry_date"]
            return [opt for opt in dated_options if opt["_expiry_date"] == max_expiry]

    def get_dte(self, index: str = "NIFTY") -> int:
        """Get days to expiry for nearest expiry."""
        options = self.get_nearest_expiry_options(index)
        if options:
            exp_date = options[0]["_expiry_date"]
            return (exp_date - datetime.now().date()).days
        return 0

    async def get_ltp(self, exchange: str, symbol: str, token: str) -> Optional[float]:
        """Get Last Traded Price via REST API."""
        if not self.authenticated:
            return None
        try:
            data = self.smart_api.ltpData(exchange, symbol, token)
            if data.get("status") and data.get("data"):
                return data["data"].get("ltp")
        except Exception as e:
            logger.error(f"LTP fetch error for {symbol}: {e}")
        return None

    async def get_option_greeks(self, name: str, expiry_date: str) -> Optional[Dict]:
        """Fetch option greeks from SmartAPI."""
        if not self.authenticated:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self.jwt_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "",
                "X-ClientPublicIP": "",
                "X-MACAddress": "",
                "X-PrivateKey": self.api_key,
            }
            payload = {"name": name, "expirydate": expiry_date}

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{API_BASE}/rest/secure/angelbroking/marketData/v1/optionGreek",
                    headers=headers,
                    json=payload,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get("status"):
                        return result.get("data")
        except Exception as e:
            logger.error(f"Option Greeks fetch error: {e}")
        return None

    async def get_market_data(self, exchange: str, tokens: List[str]) -> Optional[Dict]:
        """Get full market data (quote) for multiple tokens."""
        if not self.authenticated:
            return None
        try:
            data = self.smart_api.getMarketData(
                mode="FULL",
                exchangeTokens={exchange: tokens}
            )
            if data.get("status") and data.get("data"):
                return data["data"]
        except Exception as e:
            logger.error(f"Market data fetch error: {e}")
        return None

# ---------- Live WebSocket Engine ----------
import threading

class LiveDataEngine:
    """Manages the Angel One WebSocket connection and maintains live state."""
    
    def __init__(self, client: SmartAPIClient):
        self.client = client
        self.ws = None
        self.live_prices: Dict[str, float] = {}
        self.live_oi: Dict[str, int] = {}
        self.is_connected = False
        self._ws_thread = None
        self.on_connect = None
        import time
        self.last_tick_time = time.time()

    def _on_data(self, wsapp, message):
        """Handle incoming WebSocket data."""
        import time
        self.last_tick_time = time.time()
        if isinstance(message, dict):
            token = message.get("token")
            if not token:
                return
                
            # Mode 1, 2, 3 all have last_traded_price
            if "last_traded_price" in message:
                self.live_prices[token] = message["last_traded_price"] / 100.0  # Angel sends in paisa
                
            # Mode 3 (Snap Quote) has Open Interest
            if "open_interest" in message:
                self.live_oi[token] = message["open_interest"]
            elif "open_interest_for_the_day" in message:
                self.live_oi[token] = message["open_interest_for_the_day"]
            elif "oi" in message:
                self.live_oi[token] = message["oi"]
            elif "OpenInterest" in message:
                self.live_oi[token] = message["OpenInterest"]
    def _on_open(self, wsapp):
        logger.info("Live WebSocket CONNECTED!")
        self.is_connected = True
        if self.on_connect:
            self.on_connect()
        
    def _on_error(self, wsapp, error):
        logger.error(f"Live WebSocket ERROR: {error}")
        
    def _on_close(self, *args, **kwargs):
        logger.warning(f"Live WebSocket CLOSED {args}. Attempting to reconnect in 5 seconds...")
        self.is_connected = False
        
        def reconnect():
            import time
            time.sleep(5)
            # Prevent duplicate reconnections if it was already restarted
            if not self.is_connected:
                logger.info("Reconnecting live WebSocket...")
                self.start()
                
        threading.Thread(target=reconnect, daemon=True).start()
        
    def start(self):
        """Start the WebSocket connection in a background thread."""
        if not self.client.authenticated:
            logger.error("Cannot start WebSocket: Not authenticated")
            return
            
        from SmartApi.smartWebSocketV2 import SmartWebSocketV2
        
        self.ws = SmartWebSocketV2(
            self.client.jwt_token, 
            self.client.api_key, 
            self.client.client_id, 
            self.client.feed_token
        )
        
        self.ws.on_open = self._on_open
        self.ws.on_data = self._on_data
        self.ws.on_error = self._on_error
        self.ws.on_close = self._on_close
        
        self._ws_thread = threading.Thread(target=self.ws.connect, daemon=True)
        self._ws_thread.start()
        
    def subscribe(self, exchange_type: int, tokens: List[str], mode: int = 3):
        """Subscribe to tokens. Mode 1=LTP, 2=Quote, 3=Snap Quote (needed for OI)."""
        if not self.is_connected or not self.ws:
            logger.warning("Cannot subscribe: WebSocket not connected yet")
            return
            
        try:
            token_list = [{"exchangeType": exchange_type, "tokens": tokens}]
            self.ws.subscribe("sub_req", mode, token_list)
            logger.info(f"Subscribed to {len(tokens)} tokens in mode {mode}")
        except Exception as e:
            logger.error(f"Subscription error: {e}")

# Singleton instances
smart_client = SmartAPIClient()
live_engine = LiveDataEngine(smart_client)

