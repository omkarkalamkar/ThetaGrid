"""
ThetaGrid Backend Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'), override=True)

# Angel One SmartAPI
ANGEL_API_KEY = os.getenv("ANGEL_API_KEY", "")
ANGEL_CLIENT_ID = os.getenv("ANGEL_CLIENT_ID", "")
ANGEL_PASSWORD = os.getenv("ANGEL_PASSWORD", "")
ANGEL_TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET", "")

# Server
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", 5173))

# Instrument tokens (NSE)
NIFTY_TOKEN = "99926000"        # NIFTY 50 Index
SENSEX_TOKEN = "99919000"       # SENSEX (BSE)
VIX_TOKEN = "99926004"          # India VIX
BANKNIFTY_TOKEN = "99926009"    # Bank NIFTY
GIFT_NIFTY_TOKEN = "99926037"   # GIFT Nifty (NSE IX segment)

# Exchange types
EXCHANGE_NSE = "NSE"
EXCHANGE_BSE = "BSE"
EXCHANGE_NFO = "NFO"

# Option chain config
STRIKES_RANGE = 20  # ±20 strikes from ATM
NIFTY_STRIKE_GAP = 50
SENSEX_STRIKE_GAP = 100

# Update intervals (seconds)
GREEKS_UPDATE_INTERVAL = 30
VIX_UPDATE_INTERVAL = 5
OI_SNAPSHOT_INTERVAL = 60

def is_configured():
    """Check if Angel One credentials are configured."""
    return all([ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_PASSWORD, ANGEL_TOTP_SECRET]) and \
           ANGEL_API_KEY != "your_api_key_here"
