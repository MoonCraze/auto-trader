#  Auto Trader Bot - Multi-User Trading Platform

A sophisticated autonomous cryptocurrency trading bot with multi-user support, real-time analytics, and comprehensive trade tracking. Built with Python, React, TypeScript, and WebSocket for real-time communication.

**Demo Video:** https://www.youtube.com/watch?v=VqvUTF7BMhM

![Auto Trader Bot Demo](<./bot-ui-ts/public/demo.png>)

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
  - [Backend Components](#backend-components-python)
  - [Frontend Components](#frontend-components-react--typescript)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the Application](#running-the-application)
- [Demo Accounts](#-demo-accounts)
- [API Reference](#-api-reference)
  - [REST API Endpoints](#rest-api-endpoints)
  - [WebSocket Protocol](#websocket-protocol)
- [Project Structure](#-project-structure)
- [Database Schema](#-database-schema)
- [Configuration](#-configuration)
- [Technology Stack](#-technology-stack)
- [Documentation](#-documentation)
- [Contributing](#-contributing)

---

## ✨ Features

### 🔐 Authentication System
- **Synthetic Wallet Generation**: Random SOL balance (10-20 SOL) assigned per user
- **Secure Login/Registration**: Session-based authentication flow
- **Session Persistence**: Automatic re-login on page refresh
- **Multi-User Support**: Isolated trading sessions per wallet

### 📊 Trading Dashboard
- **Real-Time Charts**: Candlestick charts with strategy overlays powered by TradingView
- **Live Monitoring**: Real-time trade execution and position tracking
- **Portfolio Tracking**: Live P&L calculations and balance updates
- **Transaction Feed**: Market-wide transaction activity display
- **Trade History**: Complete bot trade log with status indicators
- **Strategy Visualization**: Visual representation of stop-loss and take-profit levels

### 👤 Profile/Wallet Page
Comprehensive analytics dashboard with three interactive tabs:

#### Overview Tab
- Total P&L (Profit & Loss)
- Win rate with wins/losses breakdown
- Total trade count (active + finished)
- Trading volume and average trade size
- Average P&L per trade
- Largest win and largest loss
- Unique tokens traded count

#### Per-Token Statistics Tab
- Win rate per token
- Total SOL invested and returned
- Net P&L per token
- Average P&L percentage
- Best and worst trade identification

#### Trade History Tab
- Complete trade log with pagination
- Entry and exit price details
- P&L calculations in SOL and percentage
- Trade status indicators (active/finished/failed)
- Exit reasons (stop-loss, take-profit, trailing stop)
- Timestamp tracking

### 🔄 Real-Time Features
- **WebSocket Communication**: Instant bidirectional updates
- **Per-User State Management**: Isolated state for concurrent users
- **Shared Signal Processing**: Token signals distributed to all users
- **Independent Execution**: Each user's trades execute independently
- **Automatic Sentiment Analysis**: Pre-trade token sentiment validation
- **Dynamic Strategy**: Breakeven and trailing stop-loss adjustments

### 💾 Data Persistence
- **SQLite Database**: Production-ready schema with migrations support
- **Complete Trade History**: Entry/exit tracking with P&L calculations
- **Position Management**: Real-time open positions per user
- **Portfolio Snapshots**: Historical portfolio value tracking

---

## 🏗️ Architecture

The system follows a modern full-stack architecture with clear separation of concerns. See [Architecture.md](Architecture.md) for detailed documentation.

### Backend Components (Python)

| Component | File | Purpose |
|-----------|------|----------|
| **WebSocket Server** | `websocket_server.py` | Multi-user real-time communication hub with per-user state isolation |
| **REST API** | `api_server.py` | FastAPI server for analytics, trade history, and user management |
| **Database Models** | `database.py` | SQLAlchemy ORM models (Users, Trades, Positions, Snapshots) |
| **Authentication** | `auth.py` | Synthetic wallet generation and user authentication |
| **Portfolio Manager** | `portfolio_manager.py` | User-specific balance tracking and position management with DB persistence |
| **Execution Engine** | `execution_engine.py` | Trade execution simulator with database logging |
| **Strategy Engine** | `strategy_engine.py` | Trading strategy with dynamic stop-loss and tiered take-profit |
| **Sentiment Analyzer** | `sentiment_analyzer.py` | Token sentiment scoring via external API |
| **Entry Strategy** | `entry_strategy.py` | Technical analysis for entry signal confirmation |
| **Data Feeder** | `data_feeder.py` | Market data ingestion and streaming |

### Frontend Components (React + TypeScript)

| Component | File | Purpose |
|-----------|------|----------|
| **App Root** | `App.tsx` | Main application with routing, navigation, and WebSocket management |
| **Wallet Context** | `WalletContext.tsx` | Authentication state and WebSocket connection provider |
| **Login** | `Login.tsx` | User authentication UI (login/registration) |
| **Profile Page** | `ProfilePage.tsx` | Analytics dashboard with overview, per-token stats, and trade history |
| **Candlestick Chart** | `CandlestickChart.tsx` | Real-time TradingView charts with strategy overlays |
| **Trade Summary Panel** | `TradeSummaryPanel.tsx` | Trade queue and status visualization |
| **Transaction Feed** | `TransactionFeed.tsx` | Live market transaction display |
| **Info Panel** | `InfoPanel.tsx` | Portfolio and strategy information display |

---

## 🚀 Quick Start

### Prerequisites

Ensure you have the following installed:

- **Python 3.8+** (Python 3.10+ recommended)
- **Node.js 16+** (Node.js 18+ recommended)
- **npm** or **yarn** package manager
- **Git** for cloning the repository

### Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/MoonCraze/auto-trader.git
cd auto-trader
```

#### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Initialize Database
Create the database and populate with demo users:
```bash
python database.py
python test_setup.py  # Creates 3 demo users
```

#### 4. Install Frontend Dependencies
```bash
cd bot-ui-ts
npm install
cd ..
```

### Running the Application

#### Option 1: Quick Start Script (Windows)
For Windows users, use the provided batch script:
```bash
quick_start.bat
```

#### Option 2: Manual Start (Cross-Platform)
Open **three separate terminals** and run:

**Terminal 1 - WebSocket Server** (Port 8765)
```bash
python websocket_server.py
```

**Terminal 2 - REST API Server** (Port 8000)
```bash
python api_server.py
```

**Terminal 3 - Frontend Dev Server** (Port 5173)
```bash
cd bot-ui-ts
npm run dev
```

#### 5. Access the Application
Open your browser and navigate to:
```
http://localhost:5173
```

You should see the login page. Use any of the demo wallet addresses to log in.

---

## 🎮 Demo Accounts

Three demo accounts are pre-created with `test_setup.py`. Use these wallet addresses to log in:

| User | Wallet Address | Initial Balance |
|------|---------------|----------------|
| User 1 | `1V2zL8QR4g5AwFGHedav2z3G2yarV3u7Wwo3NCAHIt2l` | 12.4654 SOL |
| User 2 | `rt5MgKypna6kWZxqBg9lzqHenXtXw7Db0npLVra8Qsm2` | 12.3567 SOL |
| User 3 | `Tu4D9wkJi41rI25gr3wTUszwhRuhP56Cj2W63oHfHOdt` | 16.1658 SOL |

> 💡 **Tip**: See [DEMO_WALLETS.md](DEMO_WALLETS.md) for quick copy-paste reference.

---

## 📚 API Reference

### REST API Endpoints

Base URL: `http://localhost:8000`

#### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/register` | Create new synthetic wallet |
| `GET` | `/api/user/{wallet_address}` | Get user information |

#### Trading Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/trades/{wallet_address}` | Get trade history with pagination |
| `GET` | `/api/trades/{wallet_address}/{trade_id}` | Get specific trade details |
| `GET` | `/api/positions/{wallet_address}` | Get current open positions |

#### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/analytics/{wallet_address}/overall` | Overall trading statistics |
| `GET` | `/api/analytics/{wallet_address}/by-token` | Per-token analytics breakdown |
| `GET` | `/api/portfolio/history/{wallet_address}` | Historical portfolio values |

### WebSocket Protocol

WebSocket URL: `ws://localhost:8765`

#### Client Authentication
```json
{
  "type": "AUTH",
  "wallet_address": "your_wallet_address_here"
}
```

#### Server Authentication Response
```json
{
  "type": "AUTH_SUCCESS",
  "data": {
    "wallet_address": "1V2zL8QR4g5AwFGHedav2z3G2yarV3u7Wwo3NCAHIt2l",
    "initial_sol_balance": 12.4654,
    "created_at": "2025-12-07T10:30:00Z"
  }
}
```

#### Real-Time Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `NEW_TRADE_STARTING` | Server → Client | New trade initiated with initial candles |
| `UPDATE` | Server → Client | Price update with portfolio changes |
| `TRADE_SUMMARY_UPDATE` | Server → Client | Trade list synchronization |
| `ERROR` | Server → Client | Error notification |

---

## 📁 Project Structure

```
auto-trader/
├── Backend (Python)
│   ├── websocket_server.py      # Real-time WebSocket server
│   ├── api_server.py            # FastAPI REST API server
│   ├── orchestrator.py          # Trade orchestration (unused in multi-user)
│   ├── database.py              # SQLAlchemy ORM models
│   ├── auth.py                  # Synthetic wallet authentication
│   ├── portfolio_manager.py     # Portfolio and position management
│   ├── execution_engine.py      # Trade execution simulator
│   ├── strategy_engine.py       # Trading strategy logic
│   ├── entry_strategy.py        # Entry signal confirmation
│   ├── sentiment_analyzer.py    # Token sentiment analysis
│   ├── data_feeder.py           # Market data ingestion
│   ├── token_metadata.py        # Token symbol resolution
│   ├── sse.py                   # SSE stream client
│   ├── config.py                # Configuration parameters
│   ├── test_setup.py            # Database initialization script
│   └── requirements.txt         # Python dependencies
│
├── Frontend (React + TypeScript)
│   └── bot-ui-ts/
│       ├── src/
│       │   ├── components/
│       │   │   ├── Login.tsx              # Authentication UI
│       │   │   ├── ProfilePage.tsx        # Analytics dashboard
│       │   │   ├── CandlestickChart.tsx   # TradingView charts
│       │   │   ├── TradeSummaryPanel.tsx  # Trade list
│       │   │   ├── TransactionFeed.tsx    # Market feed
│       │   │   ├── InfoPanel.tsx          # Info display
│       │   │   ├── Card.tsx               # Reusable card component
│       │   │   └── ErrorBoundary.tsx      # Error handling
│       │   ├── context/
│       │   │   └── WalletContext.tsx      # Auth & WebSocket context
│       │   ├── App.tsx                    # Root component
│       │   ├── types.ts                   # TypeScript interfaces
│       │   ├── main.tsx                   # Entry point
│       │   └── index.css                  # Global styles
│       ├── public/
│       │   └── demo.png                   # Demo screenshot
│       ├── package.json                   # Frontend dependencies
│       ├── vite.config.ts                 # Vite configuration
│       └── tsconfig.json                  # TypeScript config
│
├── Documentation
│   ├── README.md                # This file
│   ├── Architecture.md          # System architecture details
│   ├── Challenges.md            # Known challenges and limitations
│   ├── SETUP_GUIDE.md           # Detailed setup instructions
│   ├── IMPLEMENTATION_SUMMARY.md # Implementation overview
│   ├── DEMO_WALLETS.md          # Demo account reference
│   ├── methodology.md           # Trading methodology
│   └── research_diagrams.md     # System diagrams
│
├── Data
│   └── trading_bot.db           # SQLite database (created on first run)
│
└── Scripts
    └── quick_start.bat          # Windows quick start script
```

---

## 📊 Database Schema

The system uses SQLite with a relational schema designed for multi-user trading:

### Tables

#### `users`
Stores user/wallet information
- `wallet_address` (PK) - Unique wallet identifier
- `initial_sol_balance` - Starting balance
- `created_at` - Account creation timestamp

#### `trades`
Complete trade lifecycle tracking
- `id` (PK) - Auto-incrementing trade ID
- `wallet_address` (FK) - User reference
- `token_address`, `token_symbol` - Token identification
- `status` - Trade state (active/finished/failed)
- `entry_time`, `entry_price`, `quantity`, `sol_invested` - Entry details
- `exit_time`, `exit_price`, `sol_returned` - Exit details
- `pnl_sol`, `pnl_percent` - Profit/loss calculations
- `stop_loss_price`, `take_profit_tiers`, `highest_price_seen` - Strategy state
- `exit_reason` - Why trade closed

#### `positions`
Current open positions per user
- `id` (PK) - Position ID
- `wallet_address` (FK) - User reference
- `token_address`, `token_symbol` - Token identification
- `tokens` - Token quantity held
- `cost_basis` - Average entry price
- `last_updated` - Last modification timestamp

#### `portfolio_snapshots`
Historical portfolio values for charting
- `id` (PK) - Snapshot ID
- `wallet_address` (FK) - User reference
- `timestamp` - Snapshot time
- `sol_balance` - Available SOL
- `total_value` - Total portfolio value
- `overall_pnl` - Cumulative P&L

> 📖 See [database.py](database.py) for complete schema definitions.

---

## ⚙️ Configuration

All system parameters are configured in [config.py](config.py):

### Trading Parameters
```python
INITIAL_CAPITAL_SOL = 50.0              # Starting balance for new users
RISK_PER_TRADE_PERCENT = 0.02           # Risk 2% per trade
```

### Strategy Parameters
```python
TAKE_PROFIT_TIERS = [
    (0.30, 0.33),  # At +30% profit, sell 33% of position
    (0.75, 0.33)   # At +75% profit, sell another 33%
]

INITIAL_STOP_LOSS_PERCENT = 0.15        # -15% hard stop
TRAILING_STOP_LOSS_PERCENT = 0.20       # -20% trailing stop
```

### Database Configuration
```python
DATABASE_URL = "sqlite:///./trading_bot.db"
```

### Wallet Generation
```python
MIN_SYNTHETIC_SOL = 10.0                # Minimum random balance
MAX_SYNTHETIC_SOL = 20.0                # Maximum random balance
```

### Simulation Parameters
```python
SIM_INITIAL_PRICE = 0.01                # Starting token price
SIM_DRIFT = 0.001                       # Positive price drift
SIM_VOLATILITY = 0.02                   # Price volatility
SIM_TIME_STEPS = 1000                   # Number of price updates
```

> ⚠️ **Note**: These are simulation parameters. Real trading would use actual market data.

---

## 🛠️ Technology Stack

### Backend
| Technology | Purpose |
|------------|----------|
| **Python 3.10+** | Core backend language |
| **asyncio** | Asynchronous runtime for concurrency |
| **websockets** | WebSocket server library |
| **FastAPI** | Modern REST API framework |
| **SQLAlchemy** | ORM and database abstraction |
| **Uvicorn** | ASGI server for FastAPI |
| **aiohttp** | Async HTTP client for external APIs |
| **Pandas** | Data analysis and manipulation |
| **NumPy** | Numerical computations |

### Frontend
| Technology | Purpose |
|------------|----------|
| **React 19** | UI framework |
| **TypeScript 5.8** | Type-safe JavaScript |
| **Vite** | Build tool and dev server |
| **TailwindCSS 4** | Utility-first CSS framework |
| **lightweight-charts** | TradingView charting library |
| **React Router** | Client-side routing |

### Database
| Technology | Purpose |
|------------|----------|
| **SQLite** | Development database (single-file) |
| **PostgreSQL** | Production-ready alternative |
| **Alembic** | Database migrations (optional) |

### Development Tools
- **ESLint** - JavaScript/TypeScript linting
- **Prettier** - Code formatting
- **Git** - Version control

---

## 📖 Documentation

Comprehensive documentation is available:

- **[Architecture.md](Architecture.md)** - Detailed system architecture, component breakdown, and data flow
- **[Challenges.md](Challenges.md)** - Known limitations, challenges, and improvement recommendations
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Step-by-step setup instructions
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Implementation overview and feature list
- **[methodology.md](methodology.md)** - Trading methodology and strategy explanation
- **[DEMO_WALLETS.md](DEMO_WALLETS.md)** - Quick reference for demo accounts

---

## 🤝 Contributing

This is an academic project (Final Year Project). Contributions, suggestions, and feedback are welcome!

### How to Contribute
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines
- Follow existing code style and conventions
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

---

## 📄 License

This project is for educational purposes.

## ⚠️ Disclaimer

**This is a simulation/educational project.** It does not use real funds or connect to actual blockchain networks. The synthetic wallets and trades are for demonstration purposes only.

---

**Built with ❤️ for learning and research purposes**
