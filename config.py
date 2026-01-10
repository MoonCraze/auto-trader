# Database Configuration
DATABASE_URL = "sqlite:///./trading_bot.db"  # SQLite for simplicity, can switch to PostgreSQL

# Token Metadata API Configuration
TOKEN_ENDPOINT_BASE = "https://orange-happiness-v6vgw754rp4p3prjp-5000.app.github.dev/token"

# Real OHLCV Data Configuration
# Solana pool address for real-time 1-minute candle data from GeckoTerminal
SOLANA_POOL_ADDRESS = "FFcYgSSgWHforA9rXXkA48p8YFoz8TSW85Jpo3CQHDyS"
OHLCV_POLLING_INTERVAL = 60  # Poll every 60 seconds for new 1-minute candles

# Portfolio and Risk Management
INITIAL_CAPITAL_SOL = 50.0
RISK_PER_TRADE_PERCENT = 0.02  # 2% of total capital per trade

# Synthetic Wallet Configuration
MIN_SYNTHETIC_SOL = 10.0
MAX_SYNTHETIC_SOL = 20.0

# Strategy Parameters: Tiered Take-Profits
# Format: (profit_percentage_target, portion_to_sell)
# e.g., (0.3, 0.33) means sell 33% of the position when profit hits 30%
TAKE_PROFIT_TIERS = [
    (0.30, 0.33),  # At +30% profit, sell 33%
    (0.75, 0.33)   # At +75% profit, sell another 33%
]

# Strategy Parameters: Stop-Loss
INITIAL_STOP_LOSS_PERCENT = 0.15   # 15% below entry price
TRAILING_STOP_LOSS_PERCENT = 0.20  # Trail 20% below the highest price reached

# Data Simulation Parameters
SIM_INITIAL_PRICE = 0.01
SIM_DRIFT = 0.001       # Positive drift to simulate a general uptrend
SIM_VOLATILITY = 0.02   # Volatility to create price fluctuations
SIM_TIME_STEPS = 1000    # Number of price updates in our simulation