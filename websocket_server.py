import asyncio
import websockets
import json
import random
import config
import aiohttp
from datetime import datetime, timezone

from portfolio_manager import PortfolioManager
from execution_engine import ExecutionEngine
from strategy_engine import StrategyEngine
from real_ohlcv_fetcher import get_ohlcv_fetcher, RealOHLCVFetcher
from entry_strategy import check_for_entry_signal
from token_metadata import TokenMetadata
from sentiment_analyzer import check_sentiment
from database import SessionLocal
from auth import authenticate_wallet, register_synthetic_wallet

SSE_ENDPOINT = "http://localhost:5000/stream"

# Multi-user state management
USER_STATES = {}  # wallet_address -> APP_STATE
USER_CONNECTIONS = {}  # wallet_address -> set of websockets
PORTFOLIO_MANAGERS = {}  # wallet_address -> PortfolioManager
GLOBAL_MARKET_INDEX = []  # Shared market index data for idle display
USER_LOCKS = {}  # wallet_address -> asyncio.Lock to serialize trades per user

# Real OHLCV data fetchers (per pair address)
OHLCV_FETCHERS = {}  # pair_address -> RealOHLCVFetcher
OHLCV_METADATA = {}  # pair_address -> metadata
DEFAULT_FETCHER: RealOHLCVFetcher = None  # Fallback for idle display


def user_has_active_or_pending(app_state):
    """Return True if the user currently has a trade in progress."""
    return any(s['status'] in ('Active', 'Pending') for s in app_state.get("trade_summaries", []))

def get_default_state():
    """Return a fresh APP_STATE structure for a new user"""
    return {
        "trade_summaries": [],
        "active_token_info": None,
        "initial_candles": [],
        "initial_volumes": [],
        "bot_trades": [],
        "strategy_state": None,
        "portfolio": None,
        "market_index_history": [],
        "processed_tokens": set(),
        "loss_tokens": set(),
    }

async def register(websocket):
    wallet_address = None
    db = SessionLocal()
    
    try:
        print(f"New UI client connected, waiting for authentication...")
        
        # Wait for AUTH message
        auth_message = await websocket.recv()
        auth_data = json.loads(auth_message)
        
        if auth_data.get('type') == 'AUTH':
            wallet_address = auth_data.get('wallet_address')
            
            if not wallet_address:
                await websocket.send(json.dumps({'type': 'ERROR', 'message': 'No wallet address provided'}))
                return
            
            # Authenticate or create user
            user = authenticate_wallet(wallet_address, db)
            if not user:
                await websocket.send(json.dumps({'type': 'ERROR', 'message': 'Invalid wallet address'}))
                return
            
            print(f"✅ Authenticated wallet: {wallet_address[:8]}...")
            
            # Initialize user state if not exists
            if wallet_address not in USER_STATES:
                USER_STATES[wallet_address] = get_default_state()
                USER_STATES[wallet_address]["market_index_history"] = list(GLOBAL_MARKET_INDEX)
                
            if wallet_address not in PORTFOLIO_MANAGERS:
                PORTFOLIO_MANAGERS[wallet_address] = PortfolioManager(
                    user.initial_sol_balance,
                    wallet_address=wallet_address,
                    db_session=db
                )
            
            if wallet_address not in USER_CONNECTIONS:
                USER_CONNECTIONS[wallet_address] = set()
            
            USER_CONNECTIONS[wallet_address].add(websocket)
            
            # Send authentication success with user data
            await websocket.send(json.dumps({
                'type': 'AUTH_SUCCESS',
                'data': {
                    'wallet_address': user.wallet_address,
                    'initial_sol_balance': user.initial_sol_balance,
                    'created_at': user.created_at.isoformat()
                }
            }))
            
            # Send initial state to client
            user_state = USER_STATES[wallet_address]
            await websocket.send(json.dumps({'type': 'TRADE_SUMMARY_UPDATE', 'data': {'summaries': user_state["trade_summaries"]}}))
            
            if user_state["active_token_info"]:
                start_package = {
                    'type': 'NEW_TRADE_STARTING',
                    'data': {
                        'token_info': user_state["active_token_info"],
                        'candles': user_state["initial_candles"],
                        'volumes': user_state["initial_volumes"],
                        'bot_trades': user_state["bot_trades"],
                        'strategy_state': user_state["strategy_state"],
                    }
                }
                await websocket.send(json.dumps(start_package))
                if user_state["portfolio"]:
                    await websocket.send(json.dumps({'type': 'UPDATE', 'data': {'portfolio': user_state["portfolio"]}}))
            else:
                market_index_package = {
                    'type': 'NEW_TRADE_STARTING',
                    'data': {
                        'token_info': {'symbol': 'SOL/USDC', 'address': 'MARKET_INDEX'},
                        'candles': user_state["market_index_history"],
                        'volumes': [],
                        'bot_trades': [],
                        'strategy_state': None,
                    }
                }
                await websocket.send(json.dumps(market_index_package))
            
            await websocket.wait_closed()
        else:
            await websocket.send(json.dumps({'type': 'ERROR', 'message': 'Expected AUTH message'}))
    except Exception as e:
        print(f"Error in register: {e}")
    finally:
        print(f"Connection handler finished for {wallet_address[:8] if wallet_address else 'unauthenticated'}...")
        if wallet_address and wallet_address in USER_CONNECTIONS:
            USER_CONNECTIONS[wallet_address].discard(websocket)
            if not USER_CONNECTIONS[wallet_address]:
                del USER_CONNECTIONS[wallet_address]
        db.close()

async def broadcast_to_user(wallet_address, message):
    """Broadcast message to all connections of a specific user"""
    connections = USER_CONNECTIONS.get(wallet_address)
    if not connections:
        return

    # Work on a snapshot to avoid mutation during iteration
    for conn in list(connections):
        try:
            await conn.send(message)
        except websockets.exceptions.ConnectionClosed:
            # Safely discard; guard wallet removal during race conditions
            current = USER_CONNECTIONS.get(wallet_address)
            if current:
                current.discard(conn)
                if not current:
                    USER_CONNECTIONS.pop(wallet_address, None)

async def broadcast_to_all(message):
    """Broadcast message to all connected users"""
    for wallet_address in list(USER_CONNECTIONS.keys()):
        await broadcast_to_user(wallet_address, message)

def format_candle_and_volume(row):
    timestamp = int(row['timestamp'].timestamp())
    candle = {'time': timestamp, 'open': row['open'], 'high': row['high'], 'low': row['low'], 'close': row['close']}
    volume_color = '#26a69a80' if row['close'] >= row['open'] else '#ef535080'
    volume = {'time': timestamp, 'value': row['volume'], 'color': volume_color}
    return candle, volume

def format_candle_from_dict(candle_dict):
    """Format candle from dictionary (for real OHLCV data)"""
    timestamp = candle_dict['timestamp']
    candle = {'time': timestamp, 'open': candle_dict['open'], 'high': candle_dict['high'], 'low': candle_dict['low'], 'close': candle_dict['close']}
    volume_color = '#26a69a80' if candle_dict['close'] >= candle_dict['open'] else '#ef535080'
    volume = {'time': timestamp, 'value': candle_dict['volume'], 'color': volume_color}
    return candle, volume

async def get_or_create_ohlcv_fetcher(pair_address: str) -> RealOHLCVFetcher:
    """Get existing fetcher or create new one for a pair address"""
    if pair_address in OHLCV_FETCHERS:
        return OHLCV_FETCHERS[pair_address]
    
    print(f"Creating new OHLCV fetcher for pair: {pair_address}")
    fetcher = RealOHLCVFetcher(pair_address)
    
    # Fetch initial data
    candles, metadata = await fetcher.fetch_initial_data()
    
    if candles:
        OHLCV_FETCHERS[pair_address] = fetcher
        OHLCV_METADATA[pair_address] = metadata
        print(f"✅ OHLCV fetcher created: {len(candles)} candles loaded for {metadata['base_token']['symbol']}/{metadata['quote_token']['symbol']}")
        
        # Start polling for this pair
        asyncio.create_task(fetcher.start_polling(
            lambda candle, pa=pair_address: handle_new_ohlcv_candle(candle, pa), 
            config.OHLCV_POLLING_INTERVAL
        ))
        
        return fetcher
    else:
        print(f"⚠️  Failed to fetch OHLCV data for pair: {pair_address}")
        return None

async def process_single_token(token_info, wallet_address, index, sentiment_result=None):
    """Process a token trade for a specific user using real OHLCV data"""
    if wallet_address not in PORTFOLIO_MANAGERS or wallet_address not in USER_STATES:
        print(f"Error: No portfolio manager or state for wallet {wallet_address}")
        return
    
    pm = PORTFOLIO_MANAGERS[wallet_address]
    APP_STATE = USER_STATES[wallet_address]
    executor = ExecutionEngine(pm)
    initial_sol_balance = pm.sol_balance
    initial_capital = pm.initial_capital if hasattr(pm, 'initial_capital') else pm.sol_balance
    
    print(f"[{token_info['symbol']}] Using real OHLCV data for trading...")
    
    # Check if pair_address is available
    pair_address = token_info.get('pair_address')
    
    if not pair_address:
        print(f"[{token_info['symbol']}] ERROR: No pair address available. Cannot fetch OHLCV data.")
        APP_STATE["trade_summaries"][index].update({'status': 'Failed', 'pnl': 0.0})
        await broadcast_to_user(wallet_address, json.dumps({'type': 'TRADE_SUMMARY_UPDATE', 'data': {'summaries': APP_STATE["trade_summaries"]}}))
        
        # Send message to UI to show "pair address not found" banner
        error_package = {
            'type': 'NEW_TRADE_STARTING',
            'data': {
                'token_info': token_info,
                'error': 'PAIR_ADDRESS_NOT_FOUND',
                'candles': [],
                'volumes': [],
                'bot_trades': [],
                'strategy_state': None,
            }
        }
        await broadcast_to_user(wallet_address, json.dumps(error_package))
        return
    
    # Get or create OHLCV fetcher for this pair
    fetcher = await get_or_create_ohlcv_fetcher(pair_address)
    
    if fetcher is None:
        print(f"[{token_info['symbol']}] ERROR: Failed to initialize OHLCV fetcher for pair {pair_address}")
        APP_STATE["trade_summaries"][index].update({'status': 'Failed', 'pnl': 0.0})
        await broadcast_to_user(wallet_address, json.dumps({'type': 'TRADE_SUMMARY_UPDATE', 'data': {'summaries': APP_STATE["trade_summaries"]}}))
        
        # Send error message to UI
        error_package = {
            'type': 'NEW_TRADE_STARTING',
            'data': {
                'token_info': token_info,
                'error': 'OHLCV_FETCH_FAILED',
                'candles': [],
                'volumes': [],
                'bot_trades': [],
                'strategy_state': None,
            }
        }
        await broadcast_to_user(wallet_address, json.dumps(error_package))
        return
    
    # Get all historical candles and prepare for display
    all_candles = fetcher.get_all_candles()
    print(f"[{token_info['symbol']}] Fetched {len(all_candles)} candles from OHLCV fetcher")

    print(f"[{token_info['symbol']}] [{token_info['address']}] Pair: {pair_address}")
    
    if not all_candles or len(all_candles) < 20:
        print(f"[{token_info['symbol']}] Insufficient OHLCV data (need 20, have {len(all_candles)}). Skipping.")
        APP_STATE["trade_summaries"][index].update({'status': 'Finished', 'pnl': 0.0})
        await broadcast_to_user(wallet_address, json.dumps({'type': 'TRADE_SUMMARY_UPDATE', 'data': {'summaries': APP_STATE["trade_summaries"]}}))
        return
    
    # Check for entry signal using historical data
    price_history = [candle['close'] for candle in all_candles]
    
    # TEMPORARY: Skip entry signal check to test OHLCV display
    # TODO: Re-enable entry signal after testing
    entry_signal_found = True  # check_for_entry_signal(price_history, 'sma')
    
    if not entry_signal_found:
        print(f"[{token_info['symbol']}] No entry signal found. Skipping.")
        APP_STATE["trade_summaries"][index].update({'status': 'Finished', 'pnl': 0.0})
        await broadcast_to_user(wallet_address, json.dumps({'type': 'TRADE_SUMMARY_UPDATE', 'data': {'summaries': APP_STATE["trade_summaries"]}}))
        return
    
    # Use the LATEST candle (most recent) as entry point
    entry_candle = all_candles[-1]
    entry_price = entry_candle['close']
    
    print(f"[{token_info['symbol']}] Entry signal confirmed. Entry price: {entry_price:.8f}")
    print(f"   Entry time: {entry_candle['datetime'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Prepare historical candles for UI display (all historical data)
    initial_candles = []
    initial_volumes = []
    for candle in all_candles:
        formatted_candle, formatted_volume = format_candle_from_dict(candle)
        initial_candles.append(formatted_candle)
        initial_volumes.append(formatted_volume)
    
    sol_to_invest = pm.sol_balance * config.RISK_PER_TRADE_PERCENT
    
    # Create strategy first to get parameters
    strategy = StrategyEngine(token_info, entry_price, 0)  # Temporary quantity
    strategy_params = {
        'stop_loss_price': strategy.stop_loss_price,
        'take_profit_tiers': config.TAKE_PROFIT_TIERS
    }
    
    # Get sentiment data from parameter
    sentiment_data = sentiment_result if sentiment_result else None
    
    tokens_bought = executor.execute_buy(token_info, sol_to_invest, entry_price, strategy_params, sentiment_data)
    strategy.initial_token_quantity = tokens_bought
    bot_trade = {'time': entry_candle['timestamp'], 'side': 'BUY', 'price': entry_price, 'sol_amount': sol_to_invest, 'token_amount': tokens_bought}
    strategy_state = {'entry_price': strategy.entry_price, 'stop_loss_price': strategy.stop_loss_price, 'take_profit_tiers': config.TAKE_PROFIT_TIERS, 'highest_price_seen': strategy.highest_price_seen}
    current_total = pm.get_total_value({token_info['address']: entry_price})
    portfolio_status = {
        'sol_balance': pm.sol_balance,
        'positions': {k: v for k, v in pm.positions.items()},
        'total_value': current_total,
        'trade_pnl': current_total - initial_capital,
        'overall_pnl': current_total - initial_capital
    }
    APP_STATE.update({ "active_token_info": token_info, "initial_candles": initial_candles, "initial_volumes": initial_volumes, "bot_trades": [bot_trade], "strategy_state": strategy_state, "portfolio": portfolio_status, "strategy": strategy, "executor": executor, "initial_capital": initial_capital, "initial_sol_balance": initial_sol_balance, "pair_address": pair_address })
    APP_STATE["trade_summaries"][index]['status'] = 'Active'
    await broadcast_to_user(wallet_address, json.dumps({'type': 'TRADE_SUMMARY_UPDATE', 'data': {'summaries': APP_STATE["trade_summaries"]}}))
    new_trade_package = { 'type': 'NEW_TRADE_STARTING', 'data': { 'token_info': token_info, 'candles': initial_candles, 'volumes': initial_volumes, 'bot_trades': [bot_trade], 'strategy_state': strategy_state, 'portfolio': portfolio_status } }
    await broadcast_to_user(wallet_address, json.dumps(new_trade_package))
    
    print(f"[{token_info['symbol']}] Trade active. Waiting for real-time 1-minute updates...")
    # Trade is now active and will be updated by the real-time polling loop in handle_new_ohlcv_candle()

async def handle_new_ohlcv_candle(candle_dict, pair_address: str):
    """Handle new OHLCV candle for all active trades using this pair"""
    current_price = candle_dict['close']
    candle, volume = format_candle_from_dict(candle_dict)
    
    # Update all users who have active trades with this pair address
    for wallet_address in list(USER_STATES.keys()):
        APP_STATE = USER_STATES[wallet_address]
        
        # Skip if no active token
        if not APP_STATE.get("active_token_info"):
            continue
        
        # Check if this user's active trade uses this pair address
        user_pair_address = APP_STATE.get("pair_address")
        if user_pair_address != pair_address:
            continue
        
        token_info = APP_STATE["active_token_info"]
        pm = PORTFOLIO_MANAGERS[wallet_address]
        strategy = APP_STATE.get("strategy")
        executor = APP_STATE.get("executor")
        initial_capital = APP_STATE.get("initial_capital", pm.sol_balance)
        
        if not strategy or not executor:
            continue
        
        # Check for trade action
        bot_trade_event = None
        if token_info['address'] in pm.positions:
            action, sell_portion, reason = strategy.check_for_trade_action(current_price)
            if action == 'SELL':
                remaining_tokens = pm.positions[token_info['address']]['tokens']
                tokens_to_sell = remaining_tokens if sell_portion == 1.0 else strategy.initial_token_quantity * sell_portion
                tokens_to_sell = min(tokens_to_sell, remaining_tokens)
                sol_received = executor.execute_sell(token_info, tokens_to_sell, current_price, reason)
                if sol_received > 0:
                    bot_trade_event = {'time': candle_dict['timestamp'], 'side': 'SELL', 'price': current_price, 'sol_amount': sol_received, 'token_amount': tokens_to_sell}
                    APP_STATE["bot_trades"].append(bot_trade_event)
                    print(f"[{token_info['symbol']}] {wallet_address[:8]}... executed {reason}: Sold {tokens_to_sell:.4f} tokens at {current_price:.8f}")
        
        # Update strategy state and portfolio
        APP_STATE["strategy_state"] = {'entry_price': strategy.entry_price, 'stop_loss_price': strategy.stop_loss_price, 'take_profit_tiers': config.TAKE_PROFIT_TIERS, 'highest_price_seen': strategy.highest_price_seen}
        current_total = pm.get_total_value({token_info['address']: current_price})
        APP_STATE["portfolio"] = {
            'sol_balance': pm.sol_balance,
            'positions': {k: v for k, v in pm.positions.items()},
            'total_value': current_total,
            'trade_pnl': current_total - initial_capital,
            'overall_pnl': current_total - initial_capital
        }
        
        # Generate random market trade for UI
        market_trade = {'side': 'BUY' if random.random() > 0.5 else 'SELL', 'sol_amount': round(random.uniform(0.05, 1.5), 4), 'price': round(current_price, 6), 'timestamp': datetime.now(timezone.utc).isoformat()} if random.random() > 0.6 else None
        
        # Persist candles/volumes
        APP_STATE["initial_candles"].append(candle)
        APP_STATE["initial_volumes"].append(volume)
        # Keep a reasonable history window to avoid unbounded growth
        if len(APP_STATE["initial_candles"]) > 1000:
            APP_STATE["initial_candles"] = APP_STATE["initial_candles"][-1000:]
            APP_STATE["initial_volumes"] = APP_STATE["initial_volumes"][-1000:]

        update_message = {'type': 'UPDATE', 'data': {'candle': candle, 'volume': volume, 'portfolio': APP_STATE["portfolio"], 'strategy_state': APP_STATE["strategy_state"], 'bot_trade': bot_trade_event, 'market_trade': market_trade}}
        await broadcast_to_user(wallet_address, json.dumps(update_message))
        
        # Check if trade is finished
        if token_info['address'] not in pm.positions:
            index = next((i for i, s in enumerate(APP_STATE["trade_summaries"]) if s['token']['address'] == token_info['address']), None)
            if index is not None:
                initial_sol_balance = APP_STATE.get("initial_sol_balance", initial_capital)
                print(f"[{token_info['symbol']}] Trade finished for {wallet_address[:8]}...")
                APP_STATE["trade_summaries"][index]['status'] = 'Finished'
                APP_STATE["trade_summaries"][index]['pnl'] = pm.sol_balance - initial_sol_balance
                # If loss, blacklist this token for this user for the session
                if APP_STATE["trade_summaries"][index]['pnl'] < 0:
                    APP_STATE.setdefault("loss_tokens", set()).add(token_info['address'])
                await broadcast_to_user(wallet_address, json.dumps({'type': 'TRADE_SUMMARY_UPDATE', 'data': {'summaries': APP_STATE["trade_summaries"]}}))
                
                # Clear active token
                APP_STATE["active_token_info"] = None
                APP_STATE["strategy"] = None
                APP_STATE["executor"] = None

async def listen_for_tokens(raw_queue: asyncio.Queue, metadata: TokenMetadata):
    print("Starting lean SSE listener...")
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(SSE_ENDPOINT) as response:
                    if response.status != 200:
                        print(f"SSE connection failed: {response.status}. Retrying in 10s.")
                        await asyncio.sleep(10)
                        continue
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data:'):
                            try:
                                data = json.loads(line[len('data:'):].strip())
                                token_address = data.get("tokenAddress")
                                if token_address:
                                    # Fetch the actual token name and pair address from the API
                                    symbol = token_address[:4] + "..." + token_address[-4:]  # Default fallback
                                    logo_url = ""
                                    pair_address = None  # NEW: Get pair address for OHLCV data
                                    
                                    try:
                                        async with aiohttp.ClientSession() as token_session:
                                            async with token_session.get(f"{config.TOKEN_ENDPOINT_BASE}/{token_address}", timeout=20) as token_response:
                                                if token_response.status == 200:
                                                    content_type = token_response.headers.get('Content-Type', '')
                                                    if 'application/json' in content_type:
                                                        token_data = await token_response.json()
                                                        symbol = token_data.get('symbol', symbol)
                                                        logo_url = token_data.get('logo_url', '')
                                                        pair_address = token_data.get('pair_address')  # Get pair address
                                                        print(f"Resolved token: {symbol} | Pair Address: {pair_address or 'NOT FOUND'}")
    
                                    except Exception as e:
                                        print(f"Could not fetch token data for {token_address}: {e}")
                                    
                                    # Also try to get logo from metadata if API doesn't provide it
                                    if not logo_url:
                                        logo_url = metadata.get_logo_url(token_address)
                                    
                                    token_info = {
                                        "address": token_address, 
                                        "symbol": symbol, 
                                        "logo_url": logo_url,
                                        "pair_address": pair_address  # Include pair address
                                    }
                                    
                                    print(f"Raw signal received for {symbol}. Pushing to screening queue.")
                                    await raw_queue.put(token_info)
                            except json.JSONDecodeError: pass
        except Exception as e:
            print(f"Error in SSE listener: {e}. Reconnecting in 10s.")
            await asyncio.sleep(10)

async def process_sentiment_queue(raw_queue: asyncio.Queue, trade_queue: asyncio.Queue):
    print("Starting sentiment screening processor...")
    while True:
        token_info = await raw_queue.get()
        
        # Add token to ALL active users' trade summaries (per-user dedupe + no re-trade same token)
        for wallet_address in list(USER_STATES.keys()):
            APP_STATE = USER_STATES[wallet_address]

            # Skip if user has ever seen/traded this token in this session
            if token_info['address'] in APP_STATE.get("processed_tokens", set()):
                continue

            # Skip if user previously lost on this token in this session
            if token_info['address'] in APP_STATE.get("loss_tokens", set()):
                continue

            # Also skip if already present in summaries with any status (Active, Pending, Finished, etc.)
            existing = next((s for s in APP_STATE["trade_summaries"] if s['token']['address'] == token_info['address']), None)
            if existing:
                continue

            new_summary = {
                'token': token_info.copy(),
                'status': 'Screening',
                'pnl': 0.0,
                'sentiment_score': None,
                'mention_count': None
            }
            APP_STATE["trade_summaries"].append(new_summary)
            APP_STATE["processed_tokens"].add(token_info['address'])
            await broadcast_to_user(wallet_address, json.dumps({'type': 'TRADE_SUMMARY_UPDATE', 'data': {'summaries': APP_STATE["trade_summaries"]}}))

        # Defer sentiment: queue for just-in-time screening right before trading
        print(f"Token {token_info['symbol']} queued for just-in-time sentiment screening.")
        await trade_queue.put((token_info, None))
        await asyncio.sleep(5)

async def process_trade_queue(trade_queue: asyncio.Queue):
    """Process validated tokens and execute trades for all active users"""
    while True:
        token_info_tuple = await trade_queue.get()
        token_info, _ = token_info_tuple
        pending_requeue = False

        # Execute trade for ALL active users when they are free; run sentiment right before trading
        for wallet_address in list(USER_STATES.keys()):
            APP_STATE = USER_STATES[wallet_address]
            summary_to_update = next((s for s in APP_STATE["trade_summaries"] if s['token']['address'] == token_info['address']), None)

            if not summary_to_update or summary_to_update['status'] != 'Screening':
                continue

            # If user is busy, defer and requeue this token
            if user_has_active_or_pending(APP_STATE):
                pending_requeue = True
                continue

            sentiment_result = await check_sentiment(token_info['address'], token_info['symbol'])
            # sentiment_result = {'score': 70, 'mentions': random.randint(0, 500), 'token_name': token_info['symbol']}


            if sentiment_result and sentiment_result.get('score', 0) > 60:
                if 'token_name' in sentiment_result:
                    token_info['symbol'] = sentiment_result['token_name']
                    summary_to_update['token']['symbol'] = sentiment_result['token_name']
                summary_to_update['status'] = 'Pending'
                summary_to_update['sentiment_score'] = sentiment_result['score']
                summary_to_update['mention_count'] = sentiment_result.get('mentions')
                index = APP_STATE["trade_summaries"].index(summary_to_update)
                await broadcast_to_user(wallet_address, json.dumps({'type': 'TRADE_SUMMARY_UPDATE', 'data': {'summaries': APP_STATE["trade_summaries"]}}))

                # Execute trade for this user with sentiment result (serialized per user)
                async def run_user_trade():
                    lock = USER_LOCKS.setdefault(wallet_address, asyncio.Lock())
                    async with lock:
                        await process_single_token(token_info, wallet_address, index, sentiment_result)

                asyncio.create_task(run_user_trade())
            else:
                summary_to_update['status'] = 'Failed'
                if sentiment_result:
                    if 'token_name' in sentiment_result:
                        summary_to_update['token']['symbol'] = sentiment_result['token_name']
                    summary_to_update['sentiment_score'] = sentiment_result.get('score')
                    summary_to_update['mention_count'] = sentiment_result.get('mentions')
                await broadcast_to_user(wallet_address, json.dumps({'type': 'TRADE_SUMMARY_UPDATE', 'data': {'summaries': APP_STATE["trade_summaries"]}}))

        # If any user still needs this token after they free up, requeue it with a short backoff
        if pending_requeue:
            await asyncio.sleep(10)
            await trade_queue.put((token_info, None))

        await asyncio.sleep(5)

async def stream_background_data():
    """Stream background market data using real OHLCV data"""
    print("Starting background market data stream with real OHLCV...")
    
    # Initialize with historical data from default fetcher (if available)
    if DEFAULT_FETCHER and DEFAULT_FETCHER.all_candles:
        all_candles = DEFAULT_FETCHER.get_all_candles()
        for candle in all_candles[-200:]:  # Last 200 candles for initial display
            formatted_candle, _ = format_candle_from_dict(candle)
            GLOBAL_MARKET_INDEX.append(formatted_candle)
    
    while True:
        # Get current price and create a pseudo-candle for idle display
        # This updates between 1-minute intervals to keep UI responsive
        if DEFAULT_FETCHER and DEFAULT_FETCHER.all_candles:
            last_real_candle = DEFAULT_FETCHER.all_candles[-1]
            last_price = last_real_candle['close']
            # Small random variation for display purposes
            new_price = last_price * (1 + random.normalvariate(0, 0.001))
            new_candle = {'time': int(datetime.now(timezone.utc).timestamp()), 'open': last_price, 'high': max(last_price, new_price), 'low': min(last_price, new_price), 'close': new_price}
            GLOBAL_MARKET_INDEX.append(new_candle)
            if len(GLOBAL_MARKET_INDEX) > 1000:
                GLOBAL_MARKET_INDEX.pop(0)
            
            # Broadcast to users who are idle (no active token)
            for wallet_address in list(USER_STATES.keys()):
                APP_STATE = USER_STATES[wallet_address]
                if APP_STATE["active_token_info"] is None:
                    APP_STATE["market_index_history"].append(new_candle)
                    if len(APP_STATE["market_index_history"]) > 1000:
                        APP_STATE["market_index_history"].pop(0)
                    await broadcast_to_user(wallet_address, json.dumps({'type': 'UPDATE', 'data': {'candle': new_candle}}))
        
        await asyncio.sleep(2)

async def initialize_default_fetcher():
    """Initialize the default OHLCV fetcher for idle display"""
    global DEFAULT_FETCHER
    
    print(f"Initializing default OHLCV fetcher for idle display: {config.SOLANA_POOL_ADDRESS}")
    DEFAULT_FETCHER = RealOHLCVFetcher(config.SOLANA_POOL_ADDRESS)
    
    # Fetch initial historical data
    candles, metadata = await DEFAULT_FETCHER.fetch_initial_data()
    
    if not candles:
        print("⚠️  WARNING: No initial OHLCV data loaded for default fetcher.")
    else:
        print(f"✅ Default OHLCV fetcher initialized: {len(candles)} candles loaded")
        print(f"   Trading pair: {metadata['base_token']['symbol']}/{metadata['quote_token']['symbol']}")
    
    # Start polling for new candles (for idle display only)
    asyncio.create_task(DEFAULT_FETCHER.start_polling(
        lambda candle: asyncio.create_task(asyncio.sleep(0)),  # No-op callback
        config.OHLCV_POLLING_INTERVAL
    ))

async def initialize_default_fetcher():
    """Initialize the default OHLCV fetcher for idle display"""
    global DEFAULT_FETCHER
    
    print(f"Initializing default OHLCV fetcher for idle display: {config.SOLANA_POOL_ADDRESS}")
    DEFAULT_FETCHER = RealOHLCVFetcher(config.SOLANA_POOL_ADDRESS)
    
    # Fetch initial historical data
    candles, metadata = await DEFAULT_FETCHER.fetch_initial_data()
    
    if not candles:
        print("⚠️  WARNING: No initial OHLCV data loaded for default fetcher.")
    else:
        print(f"✅ Default OHLCV fetcher initialized: {len(candles)} candles loaded")
        print(f"   Trading pair: {metadata['base_token']['symbol']}/{metadata['quote_token']['symbol']}")
    
    # Start polling for new candles (for idle display only)
    asyncio.create_task(DEFAULT_FETCHER.start_polling(
        lambda candle: asyncio.create_task(asyncio.sleep(0)),  # No-op callback
        config.OHLCV_POLLING_INTERVAL
    ))

async def main():
    print("=== Starting Autonomous Trading System ===")
    
    # Step 1: Initialize default OHLCV fetcher for idle display
    print("Step 1: Initializing default OHLCV data fetcher...")
    await initialize_default_fetcher()
    
    # Step 2: Initialize token metadata
    print("Step 2: Initializing token metadata...")
    token_metadata = TokenMetadata()
    await token_metadata.initialize()
    
    # Step 3: Create queues
    raw_signal_queue = asyncio.Queue()
    trade_queue = asyncio.Queue()
    
    # Step 4: Start WebSocket server
    print("Step 3: Starting WebSocket server on localhost:8765...")
    server = websockets.serve(register, "localhost", 8765)
    
    print("✅ All systems initialized. Trading system is ready!")
    print("📊 Each token will use its own pair address for OHLCV data")
    print("=" * 50)
    
    # Start all async tasks
    await asyncio.gather(
        server,
        listen_for_tokens(raw_signal_queue, token_metadata),
        process_sentiment_queue(raw_signal_queue, trade_queue),
        process_trade_queue(trade_queue),
        stream_background_data()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user.")