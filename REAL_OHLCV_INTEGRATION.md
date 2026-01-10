# Real OHLCV Data Integration

## Overview
This system has been updated to use **real 1-minute OHLCV (candlestick) data** from the GeckoTerminal API instead of synthetic data. The data is fetched via RESTful GET endpoints and polled every 60 seconds.

## Changes Made

### 1. New Module: `real_ohlcv_fetcher.py`
- **Purpose**: Fetches real-time 1-minute candle data from GeckoTerminal API
- **Features**:
  - Initial historical data load (up to 1000 candles)
  - Automatic 1-minute polling for new candles
  - Proper timestamp handling
  - Candle data caching for reconnecting clients
  
### 2. Updated: `config.py`
Added configuration for real OHLCV data:
```python
SOLANA_POOL_ADDRESS = "FFcYgSSgWHforA9rXXkA48p8YFoz8TSW85Jpo3CQHDyS"
OHLCV_POLLING_INTERVAL = 60  # Poll every 60 seconds
```

### 3. Updated: `websocket_server.py`
Major changes:
- Removed `generate_synthetic_data` import
- Added `RealOHLCVFetcher` integration
- Updated `process_single_token()` to use real historical data
- Added `handle_new_ohlcv_candle()` to process new 1-minute candles for all active trades
- Updated `stream_background_data()` to use real data for idle display
- Added `initialize_ohlcv_fetcher()` to load historical data on startup

## How It Works

### Data Flow
1. **Startup**: System fetches up to 1000 historical 1-minute candles from GeckoTerminal
2. **Display**: All historical candles are shown on the chart
3. **Trading**: Entry signals are checked using the historical data, but trading starts at the LATEST candle (current time)
4. **Updates**: Every 60 seconds, the system polls for new candles and updates all active trades

### API Endpoint
```
https://api.geckoterminal.com/api/v2/networks/solana/pools/{POOL_ADDRESS}/ohlcv/minute?aggregate=1&limit=1000
```

### Response Format
```json
{
  "data": {
    "attributes": {
      "ohlcv_list": [
        [timestamp, open, high, low, close, volume],
        ...
      ]
    }
  },
  "meta": {
    "base": {"address": "...", "name": "...", "symbol": "..."},
    "quote": {"address": "...", "name": "...", "symbol": "..."}
  }
}
```

**Note**: The API returns candles in **reverse chronological order** (latest first). The fetcher automatically reverses this to oldest→newest for proper chart display.

## Configuration

### Changing the Token Pool
Edit `config.py` and update:
```python
SOLANA_POOL_ADDRESS = "YOUR_POOL_ADDRESS_HERE"
```

To find a pool address:
1. Visit [GeckoTerminal](https://www.geckoterminal.com/)
2. Search for your token
3. Copy the pool address from the URL

### Adjusting Polling Interval
Edit `config.py`:
```python
OHLCV_POLLING_INTERVAL = 60  # Seconds (60 = 1 minute)
```
**Recommendation**: Keep at 60 seconds to match 1-minute candles

## Key Features

### Historical Data Display
- All fetched historical candles are displayed on the chart
- Users can see price history before the trade starts
- Smooth scrolling and zooming on the chart

### Live Trading
- Trading decisions are made in real-time at the LATEST candle
- Each new 1-minute candle triggers strategy checks (stop-loss, take-profit)
- Updates are broadcast to all connected users instantly

### Multi-User Support
- Each user's active trades are updated with new candles
- Trades complete automatically when positions are closed
- Users can reconnect and see full trade history

## Testing

### Test the OHLCV Fetcher
```bash
python real_ohlcv_fetcher.py
```

This will:
1. Fetch initial historical data
2. Display candle information
3. Poll for updates 3 times (for demo)

### Verify Integration
1. Start the trading system: `python websocket_server.py`
2. Check console output for:
   ```
   Initializing real OHLCV fetcher for pool: FFc...
   ✅ OHLCV data initialized: 176 candles loaded
   Starting OHLCV polling every 60 seconds...
   ```
3. Monitor for new candles every minute:
   ```
   📊 New candle: 2026-01-10 09:40:00 UTC | O:0.00179016 H:0.00181171 ...
   ```

## Removed Components
- `data_feeder.py` - No longer used (kept for reference)
- Synthetic data generation from `websocket_server.py`
- All references to `generate_synthetic_data()`

## Benefits
1. **Real Market Data**: Trade with actual market prices and volumes
2. **Accurate Backtesting**: Historical data allows realistic entry signal detection
3. **Live Updates**: New candles every minute keep trades current
4. **Transparency**: See exactly what the market is doing in real-time

## Troubleshooting

### No data loading
- Check internet connection
- Verify pool address is correct
- Check GeckoTerminal API status

### Candles not updating
- Verify polling interval is set correctly
- Check console for error messages
- Ensure WebSocket connection is active

### Wrong token data
- Update `SOLANA_POOL_ADDRESS` in config.py
- Restart the system to load new pool data

## Future Enhancements
- Support for multiple timeframes (5min, 15min, 1hour)
- Automatic pool address detection from token address
- Fallback to alternative data sources
- Rate limiting and error handling improvements
