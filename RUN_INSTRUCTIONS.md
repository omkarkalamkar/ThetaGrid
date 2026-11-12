# ThetaGrid - Options Selling Intelligence Dashboard

## Quick Start Commands

### Option 1: Simple Shell Script (Recommended)
```bash
# Make it executable if not already
chmod +x start.sh

# Run it
./start.sh
```

### Option 2: Python Runner (More Features)
```bash
# Make it executable if not already
chmod +x run.py

# Run it
python3 run.py
# or
./run.py
```

### Option 3: Manual Start (Separate Terminals)

**Terminal 1 - Backend:**
```bash
cd /Users/omkar/Documents/ThetaGrid/backend
source .venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd /Users/omkar/Documents/ThetaGrid/frontend
npm run dev
```

## Access URLs

Once running, access the application at:
- **Dashboard:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **WebSocket:** ws://localhost:8000/ws (live data)

## Features Running

✅ **Live Market Data:**
- NIFTY spot and options
- SENSEX spot and options  
- INDIA VIX
- Gift Nifty (scraped from giftnifty.org)

✅ **Analytics:**
- Option chain with live prices
- OI buildup analysis
- ATM straddle premium tracking
- PCR, Max Pain, Expected Move
- Greeks (Delta, Gamma, Theta, Vega)

✅ **Angel One Integration:**
- Live WebSocket data
- Option token subscriptions
- Position tracking

## Prerequisites Check

Before running, ensure:
1. **Python virtual environment exists:**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Node.js dependencies installed:**
   ```bash
   cd frontend
   npm install
   ```

3. **Environment variables** (optional for live data):
   - Copy `.env.example` to `.env` in project root
   - Add your Angel One credentials for live trading data

## Stopping the Application

Press **Ctrl+C** in the terminal where you started the services.

## Troubleshooting

### Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000

# Check what's using port 5173  
lsof -i :5173

# Kill processes if needed
pkill -f "uvicorn.*8000"
pkill -f "npm.*dev"
```

### Backend Won't Start
```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt  # Reinstall dependencies
```

### Frontend Won't Start
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## API Endpoints

- `GET /api/market` - Live market snapshot
- `GET /api/option-chain/{NIFTY|SENSEX}` - Option chain data
- `GET /api/buildup/{NIFTY|SENSEX}` - OI buildup summary
- `GET /api/straddle-history/{NIFTY|SENSEX}` - Straddle premium history
- `GET /api/positions` - Angel One positions
- `GET /api/status` - System status

## Development

- **Backend:** Python + FastAPI + WebSockets
- **Frontend:** React + Vite + Chart.js
- **Data Source:** Angel One SmartAPI + Web scraping
- **Database:** In-memory + JSON file persistence