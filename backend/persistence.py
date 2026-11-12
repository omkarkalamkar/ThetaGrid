import json
import os
from datetime import datetime
from pydantic import BaseModel

PERSISTENCE_FILE = "market_persistence.json"

class MarketData(BaseModel):
    prev_close: dict = {"NIFTY": 22700.0, "SENSEX": 75000.0, "VIX": 13.5}
    last_traded: dict = {"NIFTY": 22700.0, "SENSEX": 75000.0, "VIX": 13.5}
    last_date: str = ""

def load_persistence() -> MarketData:
    if os.path.exists(PERSISTENCE_FILE):
        try:
            with open(PERSISTENCE_FILE, "r") as f:
                return MarketData(**json.load(f))
        except:
            pass
    return MarketData()

def save_persistence(data: MarketData):
    with open(PERSISTENCE_FILE, "w") as f:
        json.dump(data.model_dump(), f, indent=4)

def update_persistence(live_nifty, live_sensex, live_vix) -> dict:
    data = load_persistence()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if data.last_date and data.last_date != today_str:
        # It's a new day! Move last_traded to prev_close
        data.prev_close = data.last_traded.copy()
        
    data.last_date = today_str
    if live_nifty: data.last_traded["NIFTY"] = live_nifty
    if live_sensex: data.last_traded["SENSEX"] = live_sensex
    if live_vix: data.last_traded["VIX"] = live_vix
    
    save_persistence(data)
    return data.prev_close
