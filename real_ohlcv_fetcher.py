"""
Real OHLCV Data Fetcher for GeckoTerminal API
Fetches real 1-minute candle data for Solana token pools
"""
import asyncio
import aiohttp
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
import config

class RealOHLCVFetcher:
    """
    Fetches real 1-minute OHLCV data from GeckoTerminal API.
    Handles initial historical data load and continuous 1-minute updates.
    """
    
    def __init__(self, pool_address: str):
        """
        Initialize the fetcher with a specific pool address.
        
        Args:
            pool_address: The Solana pool address (e.g., FFcYgSSgWHforA9rXXkA48p8YFoz8TSW85Jpo3CQHDyS)
        """
        self.pool_address = pool_address
        self.base_url = "https://api.geckoterminal.com/api/v2"
        self.last_candle_timestamp = None
        self.all_candles = []  # Store all candles for reconnecting clients
        self.session = None
        
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _parse_ohlcv_data(self, raw_data: Dict) -> Tuple[List[Dict], Dict]:
        """
        Parse the raw API response into candles and metadata.
        
        Args:
            raw_data: Raw JSON response from GeckoTerminal API
            
        Returns:
            Tuple of (candles_list, metadata_dict)
        """
        candles = []
        ohlcv_list = raw_data.get('data', {}).get('attributes', {}).get('ohlcv_list', [])
        
        # Note: GeckoTerminal returns candles with LATEST FIRST
        # Format: [timestamp, open, high, low, close, volume]
        for item in ohlcv_list:
            timestamp, open_price, high, low, close, volume = item
            
            candle = {
                'timestamp': timestamp,
                'datetime': datetime.fromtimestamp(timestamp, tz=timezone.utc),
                'open': float(open_price),
                'high': float(high),
                'low': float(low),
                'close': float(close),
                'volume': float(volume)
            }
            candles.append(candle)
        
        # Get metadata about the token pair
        meta = raw_data.get('meta', {})
        metadata = {
            'base_token': {
                'address': meta.get('base', {}).get('address'),
                'name': meta.get('base', {}).get('name'),
                'symbol': meta.get('base', {}).get('symbol')
            },
            'quote_token': {
                'address': meta.get('quote', {}).get('address'),
                'name': meta.get('quote', {}).get('name'),
                'symbol': meta.get('quote', {}).get('symbol')
            }
        }
        
        return candles, metadata
    
    async def fetch_initial_data(self) -> Tuple[List[Dict], Dict]:
        """
        Fetch initial historical OHLCV data.
        
        Returns:
            Tuple of (candles_list, metadata_dict)
            Candles are ordered from oldest to newest for display
        """
        await self._ensure_session()
        
        url = f"{self.base_url}/networks/solana/pools/{self.pool_address}/ohlcv/minute"
        params = {
            'aggregate': '1',  # 1 minute candles
            'limit': '1000'     # Maximum allowed
        }
        
        try:
            print(f"Fetching initial OHLCV data from GeckoTerminal for pool {self.pool_address}...")
            async with self.session.get(url, params=params, timeout=30) as response:
                if response.status != 200:
                    print(f"Error fetching OHLCV data: HTTP {response.status}")
                    text = await response.text()
                    print(f"Response: {text[:500]}")
                    return [], {}
                
                data = await response.json()
                candles, metadata = self._parse_ohlcv_data(data)
                
                if not candles:
                    print("No candles received from API")
                    return [], metadata
                
                # Reverse to get oldest -> newest order
                candles.reverse()
                
                # Store for reconnecting clients
                self.all_candles = candles.copy()
                
                # Track the latest timestamp
                self.last_candle_timestamp = candles[-1]['timestamp']
                
                print(f"✅ Fetched {len(candles)} historical candles")
                print(f"   Oldest: {candles[0]['datetime'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print(f"   Newest: {candles[-1]['datetime'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print(f"   Token: {metadata['base_token']['symbol']}/{metadata['quote_token']['symbol']}")
                
                return candles, metadata
                
        except asyncio.TimeoutError:
            print("Timeout while fetching OHLCV data")
            return [], {}
        except Exception as e:
            print(f"Error fetching initial OHLCV data: {e}")
            return [], {}
    
    async def fetch_latest_candle(self) -> Optional[Dict]:
        """
        Fetch the latest candle data.
        Should be called every minute to get new candle.
        
        Returns:
            Latest candle dict or None if no new candle
        """
        await self._ensure_session()
        
        url = f"{self.base_url}/networks/solana/pools/{self.pool_address}/ohlcv/minute"
        params = {
            'aggregate': '1',
            'limit': '5'  # Only need a few candles to check for updates
        }
        
        try:
            async with self.session.get(url, params=params, timeout=15) as response:
                if response.status != 200:
                    print(f"Error fetching latest candle: HTTP {response.status}")
                    return None
                
                data = await response.json()
                candles, _ = self._parse_ohlcv_data(data)
                
                if not candles:
                    return None
                
                # Get the latest candle (first in the list)
                latest = candles[0]
                
                # Check if this is a new candle
                if self.last_candle_timestamp is None or latest['timestamp'] > self.last_candle_timestamp:
                    self.last_candle_timestamp = latest['timestamp']
                    self.all_candles.append(latest)
                    
                    # Keep reasonable history limit
                    if len(self.all_candles) > 1000:
                        self.all_candles = self.all_candles[-1000:]
                    
                    print(f"📊 New candle: {latest['datetime'].strftime('%Y-%m-%d %H:%M:%S UTC')} | "
                          f"O:{latest['open']:.8f} H:{latest['high']:.8f} L:{latest['low']:.8f} C:{latest['close']:.8f}")
                    
                    return latest
                else:
                    # No new candle yet
                    return None
                    
        except asyncio.TimeoutError:
            print("Timeout while fetching latest candle")
            return None
        except Exception as e:
            print(f"Error fetching latest candle: {e}")
            return None
    
    def get_current_price(self) -> Optional[float]:
        """
        Get the current price (close price of latest candle).
        
        Returns:
            Current close price or None
        """
        if self.all_candles:
            return self.all_candles[-1]['close']
        return None
    
    def get_all_candles(self) -> List[Dict]:
        """
        Get all stored candles for reconnecting clients.
        
        Returns:
            List of all candle dicts
        """
        return self.all_candles.copy()
    
    async def start_polling(self, callback, interval: int = 60):
        """
        Start continuous polling for new candles.
        
        Args:
            callback: Async function to call with new candle data
            interval: Polling interval in seconds (default 60 for 1 minute)
        """
        print(f"Starting OHLCV polling every {interval} seconds...")
        
        while True:
            try:
                await asyncio.sleep(interval)
                
                latest = await self.fetch_latest_candle()
                if latest:
                    await callback(latest)
                    
            except Exception as e:
                print(f"Error in polling loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry


# Singleton instance
_fetcher_instance: Optional[RealOHLCVFetcher] = None

def get_ohlcv_fetcher(pool_address: Optional[str] = None) -> RealOHLCVFetcher:
    """
    Get or create the singleton OHLCV fetcher instance.
    
    Args:
        pool_address: Pool address (required on first call)
        
    Returns:
        RealOHLCVFetcher instance
    """
    global _fetcher_instance
    
    if _fetcher_instance is None:
        if pool_address is None:
            raise ValueError("pool_address required for first initialization")
        _fetcher_instance = RealOHLCVFetcher(pool_address)
    
    return _fetcher_instance


# Testing
if __name__ == '__main__':
    async def test_fetcher():
        # Example pool address from the user
        pool = "FFcYgSSgWHforA9rXXkA48p8YFoz8TSW85Jpo3CQHDyS"
        
        fetcher = RealOHLCVFetcher(pool)
        
        # Test initial data fetch
        candles, metadata = await fetcher.fetch_initial_data()
        print(f"\nFetched {len(candles)} candles")
        
        if candles:
            print(f"\nFirst candle: {candles[0]}")
            print(f"Last candle: {candles[-1]}")
            print(f"\nMetadata: {metadata}")
        
        # Test polling for updates
        async def on_new_candle(candle):
            print(f"\n🔔 NEW CANDLE CALLBACK: {candle}")
        
        # Poll a few times for demo
        for i in range(3):
            print(f"\nPolling attempt {i+1}...")
            latest = await fetcher.fetch_latest_candle()
            if latest:
                await on_new_candle(latest)
            await asyncio.sleep(10)
        
        await fetcher.close()
        print("\n✅ Test complete")
    
    asyncio.run(test_fetcher())
