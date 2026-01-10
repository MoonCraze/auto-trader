import aiohttp
import asyncio


SENTIMENT_ENDPOINT_URL = "https://aryan-spectrochemical-transperitoneally.ngrok-free.dev/rag/explain"
TOKEN_INFO_ENDPOINT = "https://verbose-computing-machine-r4grwvx967vwfx6x6-5000.app.github.dev/token"
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 5

async def check_sentiment(token_address: str, token_symbol: str = None) -> dict | None:
    """
    Queries the sentiment analysis endpoint with a retry mechanism for API failures.
    It will IMMEDIATELY fail a token if the API returns insufficient data.

    Args:
        token_address: The token contract address
        token_symbol: The token symbol/name (optional, used for logging)

    Returns:
        A dictionary like {'score': 75, 'mentions': 50} on success, or None on failure.
    """
    display_name = token_symbol or token_address[:8] + "..."
    
    # First, fetch the token symbol from the token info endpoint
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{TOKEN_INFO_ENDPOINT}/{token_address}", timeout=10) as response:
                if response.status == 200:
                    token_data = await response.json()
                    token_name = token_data.get('symbol', "AWE_NAAAA")
                    print(f"[{display_name}] Resolved token name: {token_name.split()[0]}")
                else:
                    print(f"[{display_name}] Failed to fetch token info, using address instead.")
                    token_name = token_address
    except Exception as e:
        print(f"[{display_name}] Error fetching token info: {e}, using address instead.")
        token_name = "AWE_NAAAA"
    
    params = {'coin': "$"+token_name, 'max_results': 300}
    
    for attempt in range(MAX_RETRIES):
        print(f"[{token_name}] Checking sentiment (Attempt {attempt + 1}/{MAX_RETRIES})...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(SENTIMENT_ENDPOINT_URL, params=params, timeout=60) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check if token was found
                        found = data.get('found', False)
                        if not found:
                            print(f"[{display_name}] Token not found in sentiment database.")
                            return None
                        
                        # Extract sentiment data from the new API structure
                        confidence = data.get('confidence', 0)
                        evidence = data.get('evidence', 0)
                        
                        # Get twitter sentiment details
                        twitter_details = data.get('twitter_details', {})
                        twitter_total = twitter_details.get('total', 0)
                        twitter_pos_pct = twitter_details.get('pos_pct', 0)
                        
                        # Use raw data for more details
                        raw_data = data.get('raw', {})
                        total_mentions = raw_data.get('twitter_total', 0)
                        
                        # If no mentions found, fail immediately
                        if total_mentions == 0 or evidence == 0:
                            print(f"[{display_name}] Insufficient data: {total_mentions} mentions, {evidence} evidence points.")
                            return None
                        
                        # Calculate a composite score (0-100 range)
                        # Using positive percentage from Twitter as the main score
                        sentiment_score = twitter_pos_pct if twitter_pos_pct > 0 else 0
                        
                        print(f"[{display_name}] Sentiment check successful.")
                        print(f"   Score: {sentiment_score:.2f}% positive")
                        print(f"   Mentions: {total_mentions} tweets")
                        print(f"   Confidence: {confidence:.2f}")
                        print(f"   Evidence: {evidence} sources")
                        
                        return {
                            "score": sentiment_score,
                            "mentions": total_mentions,
                            "confidence": confidence,
                            "evidence": evidence,
                            "token_name": token_name,  # Include resolved token name
                            "raw_data": data  # Include full response for debugging
                        }
                    else:
                        # This is a real API error (e.g., 500, 503). We SHOULD retry this.
                        print(f"[{display_name}] Sentiment check failed with status code: {response.status}. Retrying...")
                        response.raise_for_status() # This will trigger the except block.

        except Exception as e:
            # This block now only catches genuine connection/API errors.
            print(f"[{display_name}] An API or connection error occurred: {e}")
            if attempt < MAX_RETRIES - 1:
                delay = INITIAL_RETRY_DELAY * (2 ** attempt)
                print(f"[{display_name}] Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                print(f"[{display_name}] Max retries reached for API error. Discarding signal.")
                return None

    # This is reached if all retries fail.
    return None