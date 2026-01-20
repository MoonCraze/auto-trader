# Architecture Documentation

## Overview

The Auto Trader Bot is a sophisticated multi-user cryptocurrency trading platform that combines real-time market analysis, automated trading strategies, and comprehensive analytics. The system is built on a modern full-stack architecture with Python backend and React/TypeScript frontend, communicating through WebSocket and REST APIs.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                           │
│  (React + TypeScript + WebSocket Client + REST Client)      │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼──────────────┐
        │             │              │
        ▼             ▼              ▼
┌──────────────┐ ┌──────────┐ ┌────────────┐
│  WebSocket   │ │   REST   │ │    SSE     │
│   Server     │ │   API    │ │  Stream    │
│  (Port 8765) │ │ (Port    │ │ (External) │
│              │ │  8000)   │ │            │
└──────┬───────┘ └────┬─────┘ └─────┬──────┘
       │              │              │
       └──────────────┼──────────────┘
                      │
        ┌─────────────┴──────────────┐
        │                            │
        ▼                            ▼
┌────────────────┐         ┌──────────────────┐
│   Trading      │         │   Analytics      │
│   Engine       │         │   Engine         │
│                │         │                  │
│ - Portfolio    │         │ - Database       │
│ - Execution    │         │ - Statistics     │
│ - Strategy     │         │ - Reporting      │
│ - Sentiment    │         │                  │
└────────┬───────┘         └────────┬─────────┘
         │                          │
         └──────────┬───────────────┘
                    │
                    ▼
         ┌──────────────────┐
         │   SQLite DB      │
         │                  │
         │ - Users          │
         │ - Trades         │
         │ - Positions      │
         │ - Snapshots      │
         └──────────────────┘
```

## Component Architecture

### 1. Backend Layer (Python)

#### 1.1 WebSocket Server (`websocket_server.py`)
**Purpose**: Real-time bidirectional communication hub for live trading updates

**Key Responsibilities**:
- Multi-user connection management with per-user state isolation
- Authentication flow via WebSocket AUTH protocol
- Real-time broadcasting of trading events to connected clients
- Concurrent task orchestration using asyncio

**Architecture Pattern**: Event-driven, asynchronous publisher-subscriber

**State Management**:
```python
USER_STATES = {}           # wallet_address -> APP_STATE
USER_CONNECTIONS = {}      # wallet_address -> set of websockets
PORTFOLIO_MANAGERS = {}    # wallet_address -> PortfolioManager
USER_LOCKS = {}            # wallet_address -> asyncio.Lock
GLOBAL_MARKET_INDEX = []   # Shared market data for idle display
```

**Key Message Types**:
- `AUTH` / `AUTH_SUCCESS` - Authentication handshake
- `NEW_TRADE_STARTING` - Initiates new trade monitoring
- `UPDATE` - Real-time price/portfolio updates
- `TRADE_SUMMARY_UPDATE` - Trade list synchronization
- `ERROR` - Error notifications

#### 1.2 REST API Server (`api_server.py`)
**Purpose**: Historical data retrieval and analytics queries

**Technology**: FastAPI with SQLAlchemy ORM

**Key Endpoints**:
```
POST   /api/register                    # Register new synthetic wallet
GET    /api/user/{wallet}               # Get user details
GET    /api/trades/{wallet}             # Trade history with filters
GET    /api/analytics/overall/{wallet}  # Overall trading statistics
GET    /api/analytics/per-token/{wallet}# Per-token analytics
GET    /api/positions/{wallet}          # Current open positions
GET    /api/portfolio/history/{wallet}  # Portfolio value over time
```

**Query Capabilities**:
- Pagination support
- Status filtering (active/finished/failed)
- Date range filtering
- Aggregated analytics computation

#### 1.3 Trading Engine Components

##### Portfolio Manager (`portfolio_manager.py`)
**Design Pattern**: State Manager with Persistence Layer

**Core Responsibilities**:
- SOL balance tracking
- Position management (token holdings, cost basis)
- P&L calculations (realized and unrealized)
- Database synchronization for multi-session persistence

**Key Methods**:
```python
record_buy(token, sol_spent, tokens_received, price)
record_sell(token, tokens_sold, sol_received, price)
get_position_value(token, current_price)
get_total_value(current_prices_dict)
```

**Data Persistence**:
- Immediate synchronization to Position table
- Transaction logging in Trade table
- Periodic snapshots to PortfolioSnapshot table

##### Execution Engine (`execution_engine.py`)
**Design Pattern**: Command Pattern

**Core Responsibilities**:
- Trade execution simulation
- Slippage-free pricing (for testing)
- Database transaction management
- Trade lifecycle tracking

**Buy Flow**:
1. Validate available capital
2. Calculate token quantity
3. Update portfolio manager
4. Create Trade record in database
5. Return trade ID for tracking

**Sell Flow**:
1. Validate position availability
2. Calculate SOL received
3. Update portfolio manager
4. Update Trade record (partial or full close)
5. Record exit reason and P&L

##### Strategy Engine (`strategy_engine.py`)
**Design Pattern**: State Machine

**Core Responsibilities**:
- Entry price tracking
- Dynamic stop-loss management
- Tiered take-profit execution
- Trailing stop implementation

**Strategy Parameters** (from `config.py`):
```python
INITIAL_STOP_LOSS_PERCENT = 0.15      # -15% hard stop
TRAILING_STOP_LOSS_PERCENT = 0.20     # -20% trailing
TAKE_PROFIT_TIERS = [
    (0.30, 0.33),  # +30% -> sell 33%
    (0.75, 0.33)   # +75% -> sell 33%
]
```

**State Transitions**:
```
Entry → Monitor → Breakeven Stop → Trailing Stop → Exit
                ↓
                Take Profit Tiers (partial exits)
```

**Decision Logic**:
```python
check_for_trade_action(current_price) -> (action, portion, reason)
  - HOLD: Continue monitoring
  - SELL: Execute exit (portion: 0.0-1.0)
```

##### Sentiment Analyzer (`sentiment_analyzer.py`)
**Design Pattern**: Retry Pattern with Exponential Backoff

**Core Responsibilities**:
- Token sentiment scoring (0-100)
- Mention count tracking
- API failure resilience
- Token metadata resolution

**Integration Points**:
- External sentiment API (RAG-based)
- Token info endpoint for symbol resolution
- Jupiter token list for metadata

**Retry Logic**:
- MAX_RETRIES = 3
- Exponential backoff (5s, 10s, 20s)
- Graceful degradation on failure

#### 1.4 Data Acquisition

##### Entry Strategy (`entry_strategy.py`)
**Purpose**: Technical analysis for trade entry confirmation

**Strategies Implemented**:
1. **SMA Crossover**
   - Short-term SMA (10 periods)
   - Long-term SMA (30 periods)
   - Bullish crossover detection

2. **Breakout Detection**
   - 20-period high tracking
   - Momentum confirmation
   - Volatility filtering

##### Data Feeder (`data_feeder.py`)
**Purpose**: Market data ingestion and streaming

**Capabilities**:
- Historical OHLCV fetching from GeckoTerminal
- Real-time price streaming simulation
- Synthetic data generation for testing

**Streaming Model**:
```python
async for candle in stream_data(data_df):
    # Process price update
    current_price = candle['price']
    # Trigger strategy checks
```

##### SSE Client (`sse.py`)
**Purpose**: Token signal ingestion via Server-Sent Events

**Implementation**:
- Persistent connection to external signal provider
- Async queue-based signal processing
- Automatic reconnection on failure

#### 1.5 Authentication & Authorization (`auth.py`)

**Synthetic Wallet System**:
- Base58-like address generation (44 characters)
- Random initial SOL balance (10-20 SOL)
- Session-based authentication
- No real blockchain integration (simulation)

**Security Features**:
- Wallet address validation
- Session persistence via localStorage
- Database-backed user verification

#### 1.6 Database Layer (`database.py`)

**Technology**: SQLAlchemy ORM with SQLite

**Schema Design**:

```
Users
├── wallet_address (PK)
├── created_at
├── initial_sol_balance
└── Relationships: trades, positions, portfolio_snapshots

Trades
├── id (PK, auto-increment)
├── wallet_address (FK -> Users)
├── token_address (indexed)
├── token_symbol
├── status (active/finished/failed)
├── entry_time (indexed)
├── entry_price
├── quantity
├── sol_invested
├── exit_time
├── exit_price
├── sol_returned
├── pnl_sol
├── pnl_percent
├── stop_loss_price
├── take_profit_tiers (JSON)
├── highest_price_seen
├── initial_sentiment_score
├── initial_mention_count
└── exit_reason

Positions
├── id (PK)
├── wallet_address (FK -> Users, indexed)
├── token_address (indexed)
├── token_symbol
├── tokens
├── cost_basis
└── last_updated

PortfolioSnapshots
├── id (PK)
├── wallet_address (FK -> Users, indexed)
├── timestamp (indexed)
├── sol_balance
├── total_value
└── overall_pnl
```

**Indexing Strategy**:
- Primary indexes on foreign keys
- Time-based indexes for historical queries
- Token address indexes for per-token analytics

### 2. Frontend Layer (React + TypeScript)

#### 2.1 Application Structure

```
src/
├── main.tsx              # Entry point
├── App.tsx               # Root component & routing
├── types.ts              # TypeScript interfaces
├── context/
│   └── WalletContext.tsx # Authentication & WebSocket context
└── components/
    ├── Login.tsx         # Auth UI
    ├── ProfilePage.tsx   # Analytics dashboard
    ├── CandlestickChart.tsx
    ├── TransactionFeed.tsx
    ├── TradeSummaryPanel.tsx
    ├── InfoPanel.tsx
    └── Card.tsx
```

#### 2.2 State Management Architecture

**Context-Based Global State**:
- `WalletContext`: Authentication, WebSocket connection, user data
- Component-level state: UI-specific data (charts, forms)

**WebSocket State Synchronization**:
```typescript
useEffect(() => {
  if (wsConnection) {
    wsConnection.onmessage = (event) => {
      const message = JSON.parse(event.data);
      switch (message.type) {
        case 'NEW_TRADE_STARTING':
          // Initialize chart with historical data
        case 'UPDATE':
          // Append new candle, update portfolio
        case 'TRADE_SUMMARY_UPDATE':
          // Refresh trade list
      }
    };
  }
}, [wsConnection]);
```

#### 2.3 Key Components

##### CandlestickChart.tsx
**Technology**: TradingView Lightweight Charts

**Features**:
- Real-time candle updates without full re-render
- Dynamic price line overlays (Entry, Stop-Loss, Take-Profit)
- Responsive layout with automatic scaling
- Volume histogram integration

**Performance Optimization**:
- Chart instance reuse with `useRef`
- Incremental data updates
- Debounced resize handling

##### ProfilePage.tsx
**Architecture**: Multi-tab analytics dashboard

**Tabs**:
1. **Overview**: Overall trading statistics
   - Total P&L, win rate, trade count
   - Volume metrics, average sizes
   - Largest win/loss tracking

2. **Per-Token Stats**: Token-by-token breakdown
   - Win rate per token
   - Investment/return tracking
   - Best/worst trade identification

3. **Trade History**: Complete trade log
   - Sortable, filterable table
   - Entry/exit details
   - P&L calculations with color coding

**Data Flow**:
```
Component Mount → Fetch from REST API → Display
User Action (tab change) → Local state update
Real-time updates → WebSocket → State update → Re-render
```

##### WalletContext.tsx
**Pattern**: Provider-Consumer Context

**Responsibilities**:
- Authentication state management
- WebSocket lifecycle management
- User session persistence
- Token refresh handling

**Connection Flow**:
```
Login → Establish WS → Send AUTH → Receive AUTH_SUCCESS → Subscribe to updates
```

#### 2.4 Routing & Navigation

**Routes**:
- `/` - Trading Dashboard (default)
- `/profile` - Analytics & Trade History

**Navigation State**:
- Active route highlighting
- Wallet address display in header
- WebSocket connection indicator
- Logout functionality

### 3. Data Flow Architecture

#### 3.1 Signal Processing Pipeline

```
External SSE Stream
        ↓
[listen_for_tokens] → sentiment_queue
        ↓
[process_sentiment_queue]
        ↓
   Sentiment Check (score > threshold)
        ↓
[process_trade_queue]
        ↓
   Entry Strategy Check (SMA/Breakout)
        ↓
   Execute Buy → Create Trade Record
        ↓
[monitor_trade] (per-user task)
        ↓
   Strategy Engine Monitoring
        ↓
   Price Update Loop
        ↓
   Exit Signal → Execute Sell → Update Trade Record
```

#### 3.2 Multi-User Concurrency Model

**Per-User State Isolation**:
```python
# Each user gets their own:
- APP_STATE dictionary
- PortfolioManager instance
- Set of WebSocket connections
- asyncio.Lock for trade serialization
```

**Shared Resources**:
- Token signals (SSE stream)
- Market index data
- Database connection pool

**Concurrency Strategy**:
```python
# User A and User B can trade simultaneously
asyncio.gather(
    process_trade_for_user(user_a),
    process_trade_for_user(user_b)
)

# Each user's trades are serialized
async with USER_LOCKS[wallet_address]:
    await execute_trade()
```

#### 3.3 Real-Time Update Propagation

**Broadcasting Architecture**:
```python
async def broadcast_to_user(wallet_address, message):
    """Send message to all connections of a specific user"""
    connections = USER_CONNECTIONS.get(wallet_address)
    for ws in connections:
        await ws.send(json.dumps(message))
```

**Update Triggers**:
1. **New Trade**: When entry signal confirmed
2. **Price Update**: Every candle (5-minute intervals)
3. **Trade Event**: Buy/sell execution
4. **Portfolio Change**: Balance/position updates
5. **Trade Close**: Final P&L calculation

### 4. Configuration Management

**Configuration File** (`config.py`):
```python
# Database
DATABASE_URL = "sqlite:///./trading_bot.db"

# Portfolio
INITIAL_CAPITAL_SOL = 50.0
RISK_PER_TRADE_PERCENT = 0.02  # 2% per trade

# Wallet Generation
MIN_SYNTHETIC_SOL = 10.0
MAX_SYNTHETIC_SOL = 20.0

# Strategy
TAKE_PROFIT_TIERS = [(0.30, 0.33), (0.75, 0.33)]
INITIAL_STOP_LOSS_PERCENT = 0.15
TRAILING_STOP_LOSS_PERCENT = 0.20

# Simulation
SIM_INITIAL_PRICE = 0.01
SIM_DRIFT = 0.001
SIM_VOLATILITY = 0.02
SIM_TIME_STEPS = 1000
```

### 5. Technology Stack

#### Backend
- **Python 3.10+**: Core language
- **asyncio**: Asynchronous runtime
- **websockets**: WebSocket server
- **FastAPI**: REST API framework
- **SQLAlchemy**: ORM and database abstraction
- **aiohttp**: Async HTTP client
- **pandas/numpy**: Data analysis

#### Frontend
- **React 18**: UI framework
- **TypeScript**: Type-safe JavaScript
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Styling framework
- **lightweight-charts**: TradingView charts

#### Database
- **SQLite**: Development database
- **Alembic**: Database migrations (optional)

#### Development Tools
- **ESLint**: JavaScript/TypeScript linting
- **Prettier**: Code formatting
- **pytest**: Python testing

### 6. Deployment Architecture

**Development Mode**:
```
Terminal 1: python websocket_server.py
Terminal 2: uvicorn api_server:app --reload --port 8000
Terminal 3: cd bot-ui-ts && npm run dev
```

**Process Management**:
- WebSocket server on port 8765
- REST API server on port 8000
- Vite dev server on port 5173
- SSE mock server on port 5000 (if testing)

**Data Persistence**:
- SQLite file: `trading_bot.db`
- Automatic schema creation on first run
- No migrations required for development

### 7. Security Considerations

**Current Implementation** (Development/Demo):
- Synthetic wallets (no real funds)
- No encryption on WebSocket
- CORS wide open for development
- No rate limiting

**Production Recommendations**:
- WSS (WebSocket Secure) with TLS
- API key authentication
- Rate limiting on endpoints
- CORS restriction to specific origins
- Database encryption at rest
- Input validation and sanitization
- SQL injection protection (via ORM)

### 8. Scalability Considerations

**Current Limitations**:
- SQLite (single-file, limited concurrency)
- In-memory state (not distributed)
- Single-server architecture

**Scaling Path**:
1. **Database**: Migrate to PostgreSQL
2. **State Management**: Redis for session storage
3. **Load Balancing**: Multiple WebSocket servers
4. **Message Queue**: RabbitMQ/Redis for signal distribution
5. **Containerization**: Docker + Kubernetes
6. **Monitoring**: Prometheus + Grafana

### 9. Error Handling & Resilience

**Backend Error Handling**:
- Try-catch blocks around external API calls
- Exponential backoff for retries
- Graceful WebSocket disconnection handling
- Database transaction rollback on errors

**Frontend Error Handling**:
- ErrorBoundary components
- WebSocket reconnection logic
- API request timeout handling
- User-friendly error messages

**Logging Strategy**:
- Console logging for development
- Structured logging recommended for production
- Trade execution audit trail in database

### 10. Testing Strategy

**Current Testing**:
- `test_setup.py`: Database initialization and demo user creation
- Manual testing via UI

**Recommended Testing**:
- Unit tests for strategy logic
- Integration tests for API endpoints
- WebSocket connection tests
- End-to-end UI testing with Cypress
- Load testing for concurrent users

## Conclusion

The Auto Trader Bot demonstrates a well-architected, modern full-stack application with clear separation of concerns, robust real-time communication, and comprehensive data persistence. The system is designed for extensibility and can be scaled to production with appropriate infrastructure enhancements.
