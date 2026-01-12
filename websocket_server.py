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
from data_feeder import generate_synthetic_data
from entry_strategy import check_for_entry_signal
from token_metadata import TokenMetadata
from sentiment_analyzer import check_sentiment
from database import SessionLocal
from auth import authenticate_wallet, register_synthetic_wallet

SSE_ENDPOINT = "https://helius.sarislabs.com/stream/coordinated"
# SSE_ENDPOINT = "http://localhost:5000/stream"

# Multi-user state management
USER_STATES = {}  # wallet_address -> APP_STATE
USER_CONNECTIONS = {}  # wallet_address -> set of websockets
PORTFOLIO_MANAGERS = {}  # wallet_address -> PortfolioManager
GLOBAL_MARKET_INDEX = []  # Shared market index data for idle display
USER_LOCKS = {}  # wallet_address -> asyncio.Lock to serialize trades per user


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

async def process_single_token(token_info, wallet_address, index, sentiment_result=None):
    """Process a token trade for a specific user"""
    if wallet_address not in PORTFOLIO_MANAGERS or wallet_address not in USER_STATES:
        print(f"Error: No portfolio manager or state for wallet {wallet_address}")
        return
    
    pm = PORTFOLIO_MANAGERS[wallet_address]
    APP_STATE = USER_STATES[wallet_address]
    executor = ExecutionEngine(pm)
    initial_sol_balance = pm.sol_balance
    initial_capital = pm.initial_capital if hasattr(pm, 'initial_capital') else pm.sol_balance
    print(f"[{token_info['symbol']}] Preparing data and finding entry signal...")
    data_df = generate_synthetic_data(config.SIM_INITIAL_PRICE, config.SIM_DRIFT, config.SIM_VOLATILITY, config.SIM_TIME_STEPS)
    price_history, entry_price, entry_index = [], 0.0, -1
    for i, row in data_df.iterrows():
        price_history.append(row['close'])
        if check_for_entry_signal(price_history, 'sma'):
            entry_price, entry_index = row['close'], i
            break
    if not entry_price:
        print(f"[{token_info['symbol']}] No entry signal found in dataset. Skipping.")
        APP_STATE["trade_summaries"][index].update({'status': 'Finished', 'pnl': 0.0})
        await broadcast_to_user(wallet_address, json.dumps({'type': 'TRADE_SUMMARY_UPDATE', 'data': {'summaries': APP_STATE["trade_summaries"]}}))
        return

    print(f"[{token_info['symbol']}] Entry signal found at index {entry_index}. Going live.")
    # Remove historical data - start fresh from entry point, but keep accumulating so UI can reload mid-trade
    initial_candles, initial_volumes = [], []
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
    bot_trade = {'time': int(data_df.iloc[entry_index]['timestamp'].timestamp()), 'side': 'BUY', 'price': entry_price, 'sol_amount': sol_to_invest, 'token_amount': tokens_bought}
    strategy_state = {'entry_price': strategy.entry_price, 'stop_loss_price': strategy.stop_loss_price, 'take_profit_tiers': config.TAKE_PROFIT_TIERS, 'highest_price_seen': strategy.highest_price_seen}
    current_total = pm.get_total_value({token_info['address']: entry_price})
    portfolio_status = {
        'sol_balance': pm.sol_balance,
        'positions': {k: v for k, v in pm.positions.items()},
        'total_value': current_total,
        'trade_pnl': current_total - initial_capital,
        'overall_pnl': current_total - initial_capital
    }
    APP_STATE.update({ "active_token_info": token_info, "initial_candles": initial_candles, "initial_volumes": initial_volumes, "bot_trades": [bot_trade], "strategy_state": strategy_state, "portfolio": portfolio_status })
    APP_STATE["trade_summaries"][index]['status'] = 'Active'
    await broadcast_to_user(wallet_address, json.dumps({'type': 'TRADE_SUMMARY_UPDATE', 'data': {'summaries': APP_STATE["trade_summaries"]}}))
    new_trade_package = { 'type': 'NEW_TRADE_STARTING', 'data': { 'token_info': token_info, 'candles': initial_candles, 'volumes': initial_volumes, 'bot_trades': [bot_trade], 'strategy_state': strategy_state, 'portfolio': portfolio_status } }
    await broadcast_to_user(wallet_address, json.dumps(new_trade_package))
    await asyncio.sleep(2)

    for i, row in data_df.iloc[entry_index + 1:].iterrows():
        await asyncio.sleep(1)
        current_price = row['close']
        bot_trade_event = None
        if token_info['address'] in pm.positions:
            action, sell_portion, reason = strategy.check_for_trade_action(current_price)
            if action == 'SELL':
                remaining_tokens = pm.positions[token_info['address']]['tokens']
                tokens_to_sell = remaining_tokens if sell_portion == 1.0 else strategy.initial_token_quantity * sell_portion
                tokens_to_sell = min(tokens_to_sell, remaining_tokens)
                sol_received = executor.execute_sell(token_info, tokens_to_sell, current_price, reason)
                if sol_received > 0:
                    bot_trade_event = {'time': int(row['timestamp'].timestamp()), 'side': 'SELL', 'price': current_price, 'sol_amount': sol_received, 'token_amount': tokens_to_sell}
                    APP_STATE["bot_trades"].append(bot_trade_event)
        
        APP_STATE["strategy_state"] = {'entry_price': strategy.entry_price, 'stop_loss_price': strategy.stop_loss_price, 'take_profit_tiers': config.TAKE_PROFIT_TIERS, 'highest_price_seen': strategy.highest_price_seen}
        current_total = pm.get_total_value({token_info['address']: current_price})
        APP_STATE["portfolio"] = {
            'sol_balance': pm.sol_balance,
            'positions': {k: v for k, v in pm.positions.items()},
            'total_value': current_total,
            'trade_pnl': current_total - initial_capital,
            'overall_pnl': current_total - initial_capital
        }
        market_trade = {'side': 'BUY' if random.random() > 0.5 else 'SELL', 'sol_amount': round(random.uniform(0.05, 1.5), 4), 'price': round(current_price, 6), 'timestamp': datetime.now(timezone.utc).isoformat()} if random.random() > 0.6 else None
        candle, volume = format_candle_and_volume(row)
        # Persist candles/volumes so reconnecting clients get full intratrade history instead of a blank chart
        APP_STATE["initial_candles"].append(candle)
        APP_STATE["initial_volumes"].append(volume)
        # Keep a reasonable history window to avoid unbounded growth
        if len(APP_STATE["initial_candles"]) > 1000:
            APP_STATE["initial_candles"] = APP_STATE["initial_candles"][-1000:]
            APP_STATE["initial_volumes"] = APP_STATE["initial_volumes"][-1000:]

        update_message = {'type': 'UPDATE', 'data': {'candle': candle, 'volume': volume, 'portfolio': APP_STATE["portfolio"], 'strategy_state': APP_STATE["strategy_state"], 'bot_trade': bot_trade_event, 'market_trade': market_trade}}
        await broadcast_to_user(wallet_address, json.dumps(update_message))
        if token_info['address'] not in pm.positions: break

    print(f"[{token_info['symbol']}] Trade finished.")
    APP_STATE["trade_summaries"][index]['status'] = 'Finished'
    APP_STATE["trade_summaries"][index]['pnl'] = pm.sol_balance - initial_sol_balance
    # If loss, blacklist this token for this user for the session
    if APP_STATE["trade_summaries"][index]['pnl'] < 0:
        APP_STATE.setdefault("loss_tokens", set()).add(token_info['address'])
    await broadcast_to_user(wallet_address, json.dumps({'type': 'TRADE_SUMMARY_UPDATE', 'data': {'summaries': APP_STATE["trade_summaries"]}}))

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
                                    # Fetch the actual token name from the API
                                    symbol = token_address[:4] + "..." + token_address[-4:]  # Default fallback
                                    logo_url = ""
                                    try:
                                        async with aiohttp.ClientSession() as token_session:
                                            token_endpoint = "https://orange-happiness-v6vgw754rp4p3prjp-5000.app.github.dev/token"
                                            async with token_session.get(f"{token_endpoint}/{token_address}", timeout=15) as token_response:
                                                if token_response.status == 200:
                                                    content_type = token_response.headers.get('Content-Type', '')
                                                    if 'application/json' in content_type:
                                                        token_data = await token_response.json()
                                                        symbol = token_data.get('symbol', symbol)
                                                        logo_url = token_data.get('logo_url', '')
                                                        print(f"Resolved token name: {symbol}")
                                    except Exception as e:
                                        print(f"Could not fetch token name for {token_address}: {e}", )
                                    
                                    # Also try to get logo from metadata if API doesn't provide it
                                    if not logo_url:
                                        logo_url = metadata.get_logo_url(token_address)
                                    
                                    token_info = {"address": token_address, "symbol": symbol, "logo_url": logo_url}
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
                'mention_count': None,
                'sentiment_data': None
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

            # Run sentiment just-in-time
            sentiment_result = await check_sentiment(token_info['address'], token_info['symbol'])
            # sentiment_result = {'score': 70, 'mentions': random.randint(0, 500), 'token_name': token_info['symbol']}

            if sentiment_result and sentiment_result.get('score', 0) > 60:
                if 'token_name' in sentiment_result:
                    token_info['symbol'] = sentiment_result['token_name']
                    summary_to_update['token']['symbol'] = sentiment_result['token_name']
                
                # Prepare sentiment data for UI
                raw_data = sentiment_result.get('raw_data', {})
                sentiment_data = {
                    'score': sentiment_result['score'],
                    'twitter_details': raw_data.get('twitter_details'),
                    'twitter_texts': raw_data.get('raw', {}).get('twitter_texts'),
                    'sample_texts': raw_data.get('sample_texts')
                }
                
                summary_to_update['status'] = 'Pending'
                summary_to_update['sentiment_score'] = sentiment_result['score']
                summary_to_update['mention_count'] = sentiment_result.get('mentions')
                summary_to_update['sentiment_data'] = sentiment_data
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
    print("Starting background market data stream...")
    df = generate_synthetic_data(150, 0.0001, 0.005, 200)
    for _, row in df.iterrows():
        candle, _ = format_candle_and_volume(row)
        GLOBAL_MARKET_INDEX.append(candle)
    
    while True:
        # Update global market index
        if GLOBAL_MARKET_INDEX:
            last_price = GLOBAL_MARKET_INDEX[-1]['close']
            new_price = last_price * (1 + random.normalvariate(0.0001, 0.005))
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

async def main():
    token_metadata = TokenMetadata()
    await token_metadata.initialize()
    raw_signal_queue = asyncio.Queue()
    trade_queue = asyncio.Queue()
    server = websockets.serve(register, "localhost", 8765)
    print("--- Autonomous Trading System Started ---")
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