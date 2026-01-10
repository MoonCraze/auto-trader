import aiohttp

# Jupiter's Strict token list is a good source for this mapping
TOKEN_LIST_URL = "https://token.jup.ag/strict"

class TokenMetadata:
    def __init__(self):
        self.token_map = {}  # { address: {'symbol': str, 'logo_url': str} }

    async def initialize(self):
        """Fetches the token list and builds the address-to-symbol map."""
        print("Fetching token metadata from Jupiter...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(TOKEN_LIST_URL) as response:
                    if response.status == 200:
                        tokens = await response.json()
                        # Create a dictionary for fast lookups: { "address": {"symbol": str, "logo_url": str} }
                        for token in tokens:
                            self.token_map[token['address']] = {
                                'symbol': token.get('symbol', ''),
                                'logo_url': token.get('logoURI', '')
                            }
                        print(f"Successfully loaded metadata for {len(self.token_map)} tokens.")
                    else:
                        print(f"Failed to fetch token list. Status: {response.status}")
        except Exception as e:
            print(f"An error occurred while fetching token metadata: {e}")

    def get_symbol(self, address: str) -> str:
        """Returns the symbol for a given address, or a truncated address if not found."""
        token_data = self.token_map.get(address)
        if token_data:
            return token_data['symbol']
        return f"{address[:4]}...{address[-4:]}"
    
    def get_logo_url(self, address: str) -> str:
        """Returns the logo URL for a given address, or empty string if not found."""
        token_data = self.token_map.get(address)
        if token_data:
            return token_data.get('logo_url', '')
        return ''
    
    def get_token_info(self, address: str) -> dict:
        """Returns complete token info including symbol and logo_url."""
        token_data = self.token_map.get(address)
        if token_data:
            return {
                'symbol': token_data['symbol'],
                'logo_url': token_data.get('logo_url', '')
            }
        return {
            'symbol': f"{address[:4]}...{address[-4:]}",
            'logo_url': ''
        }