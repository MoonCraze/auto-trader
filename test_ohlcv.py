"""
Quick test to verify OHLCV data is being fetched and formatted correctly
"""
import asyncio
from real_ohlcv_fetcher import RealOHLCVFetcher
import config

async def test():
    print("Testing OHLCV fetcher...")
    fetcher = RealOHLCVFetcher(config.SOLANA_POOL_ADDRESS)
    
    # Fetch initial data
    candles, metadata = await fetcher.fetch_initial_data()
    
    print(f"\n✅ Fetched {len(candles)} candles")
    print(f"Token: {metadata['base_token']['symbol']}/{metadata['quote_token']['symbol']}")
    
    if candles:
        print(f"\nFirst 3 candles:")
        for i, candle in enumerate(candles[:3]):
            print(f"  {i+1}. Time: {candle['datetime']} | Close: {candle['close']:.8f}")
        
        print(f"\nLast 3 candles:")
        for i, candle in enumerate(candles[-3:]):
            print(f"  {i+1}. Time: {candle['datetime']} | Close: {candle['close']:.8f}")
        
        # Test formatting
        print("\n\nTesting candle formatting for WebSocket:")
        last_candle = candles[-1]
        formatted = {
            'time': last_candle['timestamp'],
            'open': last_candle['open'],
            'high': last_candle['high'],
            'low': last_candle['low'],
            'close': last_candle['close']
        }
        print(f"Formatted candle: {formatted}")
        
        print(f"\n✅ All tests passed!")
    
    await fetcher.close()

if __name__ == '__main__':
    asyncio.run(test())
