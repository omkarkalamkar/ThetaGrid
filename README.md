# ThetaGrid - Options Selling Intelligence Dashboard

![ThetaGrid Banner](https://img.shields.io/badge/ThetaGrid-Options%20Dashboard-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-green?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-blue?style=flat-square)
![React](https://img.shields.io/badge/React-19+-purple?style=flat-square)

A professional **real-time options trading dashboard** for Indian markets (NIFTY & SENSEX) with live market data, option chain analysis, OI buildup tracking, and advanced analytics.

## 🚀 Features

### Live Market Data
- **NIFTY** & **SENSEX** spot prices with real-time updates
- **INDIA VIX** tracking
- **Gift Nifty** prices (scraped from giftnifty.org)
- **ATM Straddle Premium** tracking with VWAP
- **Synthetic Future** calculation for accurate ATM identification

### Option Chain Analytics
- Live option chain with ±15 strikes from ATM
- Real-time **Greeks** (Delta, Gamma, Theta, Vega)
- **Open Interest (OI)** tracking and changes
- **OI Buildup Analysis** (Long/Short Buildup, Unwinding, Covering)
- **OI Heatmap** for visual analysis
- **Call/Put Delta** distribution

### Key Metrics
- **PCR (Put-Call Ratio)**
- **Max Pain** calculation
- **OI Support & Resistance** levels
- **Expected Move** based on ATM IV
- **IV Percentile** gauge
- **Straddle Premium History** with charts

### Integration
- **Angel One SmartAPI** WebSocket integration
- Live position tracking
- Auto-reconnection and health monitoring
- Demo mode for testing without credentials

## 📦 Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI** - Modern async web framework
- **WebSocket** - Real-time data streaming
- **Angel One SmartAPI** - Market data feed
- **Uvicorn** - ASGI server

### Frontend
- **React 19+** - UI framework
- **Vite** - Build tool
- **Chart.js** - Charting library
- **Lightweight Charts** - Advanced charting

## 🔧 Installation & Setup

### Prerequisites
- Python 3.11 or higher
- Node.js 18 or higher
- Angel One SmartAPI credentials (optional for live data)

### Quick Start (Local Development)

#### Option 1: Simple Shell Script (Recommended)
```bash
chmod +x start.sh
./start.sh
```

#### Option 2: Python Runner
```bash
chmod +x run.py
python3 run.py
```

#### Option 3: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Environment Configuration

Copy `.env.example` to `.env` and configure your Angel One credentials:

```env
# Angel One SmartAPI Credentials
ANGEL_API_KEY=your_api_key_here
ANGEL_CLIENT_ID=your_client_id_here
ANGEL_PASSWORD=your_password_here
ANGEL_TOTP_SECRET=your_totp_secret_here

# Server Config
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

**Note:** You can also configure credentials through the web UI after starting the application.

## 🌐 Access URLs

Once running, access the application at:

| Service | URL | Description |
|---------|-----|-------------|
| **Dashboard** | http://localhost:5173 | Main web interface |
| **Backend API** | http://localhost:8000 | REST API |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **WebSocket** | ws://localhost:8000/ws | Live data stream |

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Health check and mode info |
| `/api/market` | GET | Live market snapshot |
| `/api/option-chain/{NIFTY\|SENSEX}` | GET | Option chain data |
| `/api/buildup/{NIFTY\|SENSEX}` | GET | OI buildup summary |
| `/api/straddle-history/{NIFTY\|SENSEX}` | GET | Straddle premium history |
| `/api/positions` | GET | Angel One positions |
| `/api/broker/login` | POST | Save broker credentials |
| `/api/broker/logout` | POST | Clear broker credentials |
| `/ws` | WebSocket | Real-time market data stream |

## 🚀 Production Deployment

For production deployment on Oracle Cloud or any VPS, see:
- **[THETAGRID_DEPLOYMENT.md](./THETAGRID_DEPLOYMENT.md)** - Complete deployment guide

### Quick Deployment Steps:
1. Clone repository on server
2. Install Python 3.11+ and Node.js 18+
3. Setup backend virtual environment
4. Build frontend for production
5. Configure PM2 for process management
6. Setup Nginx as reverse proxy
7. Configure SSL with Certbot (optional)
8. Setup DNS (e.g., thetagrid.peerpays.in)

## 🔐 Security Notes

- **Never commit `.env` file** to version control
- Use **strong passwords** for broker credentials
- Enable **firewall (UFW)** in production
- Setup **SSL/HTTPS** for production deployments
- Regularly update system packages
- Monitor PM2 logs for suspicious activity

## 🛠️ Development

### Project Structure
```
ThetaGrid/
├── backend/
│   ├── main.py              # FastAPI app & WebSocket server
│   ├── config.py            # Configuration management
│   ├── calculations.py      # Options analytics functions
│   ├── smartapi_client.py   # Angel One integration
│   ├── persistence.py       # Data persistence
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main React component
│   │   ├── components/      # UI components
│   │   └── index.css        # Styles
│   ├── package.json         # Node dependencies
│   └── vite.config.js       # Vite configuration
├── .env.example             # Environment template
├── start.sh                 # Quick start script
├── run.py                   # Python runner
└── README.md                # This file
```

### Running Tests
```bash
# Backend tests (if implemented)
cd backend
pytest

# Frontend linting
cd frontend
npm run lint
```

### Building for Production
```bash
# Build frontend
cd frontend
npm run build

# Preview production build
npm run preview
```

## 📈 Trading Strategy Features

### OI Buildup Classification
- **Long Buildup** (Bullish for Puts, Bearish for Calls): Price ↑ & OI ↑
- **Short Buildup** (Bearish for Puts, Bullish for Calls): Price ↓ & OI ↑
- **Long Unwinding** (Bearish for Puts, Bullish for Calls): Price ↓ & OI ↓
- **Short Covering** (Bullish for Puts, Bearish for Calls): Price ↑ & OI ↓

### Market Sentiment
Dashboard calculates overall sentiment based on:
- OTM Call/Put buildup patterns
- Net OI changes
- PCR trends
- Max Pain deviation

## 🐛 Troubleshooting

### Backend Won't Start
```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt --upgrade
python main.py
```

### Frontend Won't Start
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

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

### WebSocket Connection Issues
- Ensure backend is running
- Check firewall settings
- Verify Angel One credentials
- Check browser console for errors

### Authentication Failures
- Verify Angel One credentials in `.env`
- Check TOTP secret is correct
- Ensure API key is active
- Try re-authenticating through UI

## 📚 Documentation

- [Run Instructions](./RUN_INSTRUCTIONS.md) - Detailed local setup guide
- [Deployment Guide](./THETAGRID_DEPLOYMENT.md) - Production deployment guide
- [VIX Trade Analysis](./VIX_TRADE_ANALYSIS.md) - VIX trading strategies
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when running)

## 🔗 External Resources

- [Angel One SmartAPI Docs](https://smartapi.angelbroking.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [PM2 Documentation](https://pm2.keymetrics.io/)

## ⚠️ Disclaimer

This software is for **educational and informational purposes only**. It is **not financial advice**.

- Trading in options involves **significant risk** and may not be suitable for all investors
- Past performance does not guarantee future results
- Always conduct your own research and consult with a qualified financial advisor
- The developers are **not responsible** for any trading losses
- Use at your own risk

## 📝 License

This project is for private use only. All rights reserved.

## 🤝 Contributing

This is a private project. Contributions are not currently accepted.

## 📧 Contact

For issues or questions, please contact the repository owner.

---

**Built with ❤️ for Indian Options Traders**

**Live Demo:** https://thetagrid.peerpays.in (when deployed)

**Status:** ✅ Active Development
