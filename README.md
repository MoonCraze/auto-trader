# 🚀 Auto Trader Bot - Multi-User Trading Platform

A sophisticated autonomous cryptocurrency trading bot with multi-user support, real-time analytics, and comprehensive trade tracking. Built with Python, React, TypeScript, and WebSocket for real-time communication.

## 🔥 **NEW: Real OHLCV Data Integration**
The system now uses **real 1-minute candlestick data** from GeckoTerminal API instead of synthetic data:
- ✅ Real-time Solana token pool data
- ✅ Historical candles (up to 1000 candles)
- ✅ Automatic 1-minute polling
- ✅ Live price updates for all active trades

📖 **See [REAL_OHLCV_INTEGRATION.md](REAL_OHLCV_INTEGRATION.md) for detailed documentation**

## ✨ Features

### 🔐 **Authentication System**
- Synthetic wallet generation with random SOL balance (10-20 SOL)
- Secure login/registration flow
- Session persistence
- Multi-user support with isolated trading sessions

### 📊 **Trading Dashboard**
- Real-time candlestick charts with **live market data**
- Live trade execution and monitoring
- Portfolio tracking with P&L calculations
- Market transaction feed
- Bot trade history
- Strategy parameter visualization (stop-loss, take-profit tiers)

### 👤 **Profile/Wallet Page**
Comprehensive analytics dashboard with three sections:

#### **Overview**
- Total P&L and win rate
- Trading volume and trade count
- Average trade size and P&L per trade
- Largest win/loss statistics
- Unique tokens traded

#### **Per-Token Statistics**
- Win rate per token
- Total invested and returned amounts
- Net P&L per token
- Average P&L percentage
- Best and worst trades

#### **Trade History**
- Complete trade log with entry/exit details
- P&L calculations in SOL and percentage
- Trade status and exit reasons
- Timestamp tracking

### 🔄 **Real-Time Features**
- WebSocket-based live updates
- **Real OHLCV data from GeckoTerminal API**
- Per-user state management
- Shared token signals with independent execution
- Automatic sentiment analysis
- Dynamic strategy adjustments

### 💾 **Data Persistence**
- SQLite database with comprehensive schema
- Historical trade tracking
- Portfolio snapshots
- Position management

## 🏗️ Architecture

### **Backend (Python)**
- `websocket_server.py` - Multi-user WebSocket server with per-user state
- `api_server.py` - FastAPI REST API for analytics and historical data
- `database.py` - SQLAlchemy models (Users, Trades, Positions, Snapshots)
- `auth.py` - Synthetic wallet generation and authentication
- `portfolio_manager.py` - User-specific portfolio management with DB persistence
- `execution_engine.py` - Trade execution with database logging
- `strategy_engine.py` - Trading strategy implementation
- `sentiment_analyzer.py` - Token sentiment analysis

### **Frontend (React + TypeScript)**
- `App.tsx` - Main application with routing and navigation
- `WalletContext.tsx` - Authentication context provider
- `Login.tsx` - Login/registration UI
- `ProfilePage.tsx` - Analytics and trade history dashboard
- `CandlestickChart.tsx` - Real-time trading charts
- `TradeSummaryPanel.tsx` - Trade queue visualization

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd auto-trader
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Initialize database**
```bash
python database.py
python test_setup.py  # Creates demo users
```

4. **Install frontend dependencies**
```bash
cd bot-ui-ts
npm install
```

### Running the Application

**Option 1: Use Quick Start Script (Windows)**
```bash
quick_start.bat
```

**Option 2: Manual Start**

Open 3 terminals:

```bash
# Terminal 1 - WebSocket Server
python websocket_server.py

# Terminal 2 - API Server
python api_server.py

# Terminal 3 - Frontend
cd bot-ui-ts
npm run dev
```

Open http://localhost:5173 in your browser.

## 🎮 Demo Accounts

Three demo accounts are pre-created:

1. `1V2zL8QR4g5AwFGHedav2z3G2yarV3u7Wwo3NCAHIt2l` (12.4654 SOL)
2. `rt5MgKypna6kWZxqBg9lzqHenXtXw7Db0npLVra8Qsm2` (12.3567 SOL)
3. `Tu4D9wkJi41rI25gr3wTUszwhRuhP56Cj2W63oHfHOdt` (16.1658 SOL)

See `DEMO_WALLETS.md` for quick reference.

## 📡 API Endpoints

### Authentication
- `POST /api/register` - Create new synthetic wallet
- `GET /api/user/{wallet_address}` - Get user info

### Trading Data
- `GET /api/trades/{wallet_address}` - Get trade history
- `GET /api/trades/{wallet_address}/{trade_id}` - Get specific trade
- `GET /api/positions/{wallet_address}` - Get open positions

### Analytics
- `GET /api/analytics/{wallet_address}/overall` - Overall stats
- `GET /api/analytics/{wallet_address}/by-token` - Per-token analytics
- `GET /api/portfolio/history/{wallet_address}` - Portfolio history

## 🔌 WebSocket Protocol

**Client Authentication:**
```json
{
  "type": "AUTH",
  "wallet_address": "your_wallet_address"
}
```

**Server Response:**
```json
{
  "type": "AUTH_SUCCESS",
  "data": {
    "wallet_address": "...",
    "initial_sol_balance": 12.4654,
    "created_at": "2025-12-07T..."
  }
}
```

## 📁 Project Structure

```
auto-trader/
├── backend (Python)
│   ├── websocket_server.py
│   ├── api_server.py
│   ├── database.py
│   ├── auth.py
│   ├── portfolio_manager.py
│   ├── execution_engine.py
│   ├── strategy_engine.py
│   ├── sentiment_analyzer.py
│   ├── config.py
│   └── requirements.txt
├── bot-ui-ts/ (Frontend)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Login.tsx
│   │   │   ├── ProfilePage.tsx
│   │   │   ├── CandlestickChart.tsx
│   │   │   └── ...
│   │   ├── context/
│   │   │   └── WalletContext.tsx
│   │   ├── App.tsx
│   │   └── types.ts
│   └── package.json
├── trading_bot.db (SQLite database)
├── SETUP_GUIDE.md
├── IMPLEMENTATION_SUMMARY.md
├── DEMO_WALLETS.md
└── README.md
```

## 🗄️ Database Schema

- **users**: Wallet addresses, balances, creation dates
- **trades**: Complete trade lifecycle with entry/exit data
- **positions**: Current open positions per user
- **portfolio_snapshots**: Historical portfolio values

## ⚙️ Configuration

Edit `config.py` to customize:
- Initial capital and risk parameters
- Take-profit tiers
- Stop-loss percentages
- Database connection
- Wallet generation ranges

## 📚 Documentation

- `SETUP_GUIDE.md` - Detailed setup instructions
- `IMPLEMENTATION_SUMMARY.md` - Technical implementation details
- `DEMO_WALLETS.md` - Quick reference for demo accounts

## 🔧 Tech Stack

**Backend:**
- Python 3.8+
- WebSockets (websockets library)
- FastAPI
- SQLAlchemy
- Pandas, NumPy
- aiohttp

**Frontend:**
- React 19
- TypeScript 5.8
- Vite
- TailwindCSS 4
- lightweight-charts

**Database:**
- SQLite (development)
- PostgreSQL-ready schema

## 🛣️ Roadmap

- [ ] Portfolio value charts over time
- [ ] Trade export (CSV/JSON)
- [ ] Advanced filtering (date range, multi-token)
- [ ] Real-time profile updates via WebSocket
- [ ] Email notifications
- [ ] Custom strategy parameters per user
- [ ] Mobile responsive design
- [ ] Dark/light theme toggle

## 🤝 Contributing

This is an academic project (FYP). Contributions and suggestions are welcome!

## 📄 License

Academic/Educational Use

## 👨‍💻 Author

Final Year Project - Semester 8

---

**Built with ❤️ for autonomous cryptocurrency trading**