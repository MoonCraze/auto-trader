import React, { useState, useEffect, useRef } from 'react';
import { WalletProvider, useWallet } from './context/WalletContext';
import Login from './components/Login';
import ProfilePage from './components/ProfilePage';
import CandlestickChart from './components/CandlestickChart';
import TransactionFeed from './components/TransactionFeed';
import Card from './components/Card';
import TradeSummaryPanel from './components/TradeSummaryPanel';
import { Candle, Portfolio, BotTrade, MarketTrade, StrategyState, VolumeData, TradeSummary, TokenInfo } from './types';

const StrategyPanel: React.FC<{ state: StrategyState | null; currentPrice: number }> = ({ state, currentPrice }) => {
    if (!state) return <p className="text-gray-500">Awaiting entry signal...</p>;

    const drawdown = state.highest_price_seen > 0 ? ((state.highest_price_seen - currentPrice) / state.highest_price_seen) * 100 : 0;

    return (
        <div className="h-full grid grid-cols-2 gap-x-6 text-sm">
            {/* --- Column 1: Trade Plan --- */}
            <div className="space-y-3">
                <p className="text-gray-400 font-semibold mb-2 border-b border-gray-700/50 pb-1">Trade Plan</p>
                <div className="flex justify-between">
                    <span className="text-gray-400">Entry Price:</span>
                    <span className="font-mono text-white">{state.entry_price.toFixed(6)}</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-400">Stop-Loss:</span>
                    <span className="font-mono text-yellow-400">{state.stop_loss_price.toFixed(6)}</span>
                </div>
                <div className="pt-1">
                    <p className="text-gray-400 mb-1">Take-Profit Targets:</p>
                    <ul className="space-y-1">
                        {state.take_profit_tiers.map(([target, portion], i) => (
                            <li key={`tp-${i}`} className="flex justify-between text-gray-300">
                                <span>- Sell {portion * 100}%</span>
                                <span className="font-mono text-green-400">{(state.entry_price * (1 + target)).toFixed(6)}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            </div>

            {/* --- Column 2: Live Analysis --- */}
            <div className="space-y-3 border-l border-gray-700/50 pl-6">
                <p className="text-gray-400 font-semibold mb-2 border-b border-gray-700/50 pb-1">Live Analysis</p>
                <div className="flex justify-between">
                    <span className="text-gray-400">Peak Price:</span>
                    <span className="font-mono text-cyan-400">{state.highest_price_seen.toFixed(6)}</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-400">Drawdown:</span>
                    <span className={`font-mono ${drawdown > 0 ? 'text-red-400' : 'text-gray-400'}`}>{drawdown.toFixed(2)}%</span>
                </div>
            </div>
        </div>
    );
};


// Trading Dashboard Component (extracted from original App)
const TradingDashboard: React.FC = () => {
    const { isWsConnected, wsConnection, user } = useWallet();
    const [tradeSummaries, setTradeSummaries] = useState<TradeSummary[]>([]);
    const [activeTokenInfo, setActiveTokenInfo] = useState<TokenInfo | null>(null);
    const [initialCandles, setInitialCandles] = useState<Candle[] | null>(null);
    const [lastCandle, setLastCandle] = useState<Candle | null>(null);
    const [initialVolume, setInitialVolume] = useState<VolumeData[] | null>(null);
    const [lastVolume, setLastVolume] = useState<VolumeData | null>(null);
    const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
    const [strategyState, setStrategyState] = useState<StrategyState | null>(null);
    const [botTrades, setBotTrades] = useState<BotTrade[]>([]);
    const [marketTrades, setMarketTrades] = useState<MarketTrade[]>([]);
    const [chartError, setChartError] = useState<string | null>(null);  // NEW: Track chart errors
    const initialCapital = user?.initial_sol_balance ?? 50.0;
    const chartBootstrappedRef = useRef(false);

    useEffect(() => {
        if (!wsConnection) return;

        const handleMessage = (event: MessageEvent) => {
            const message = JSON.parse(event.data);
            switch (message.type) {
                case 'AUTH_SUCCESS':
                    console.log('Authenticated with WebSocket');
                    break;
                case 'NEW_TRADE_STARTING':
                    // Reset live updates FIRST to prevent race conditions
                    setLastCandle(null);
                    setLastVolume(null);
                    setMarketTrades([]);
                    setChartError(null);  // Clear any previous errors
                    chartBootstrappedRef.current = false; // Reset bootstrap flag for new token
                    
                    // Then update token data
                    const tradeData = message.data;
                    
                    // Check for errors (pair address not found, etc.)
                    if (tradeData.error) {
                        setChartError(tradeData.error);
                        setActiveTokenInfo(tradeData.token_info);
                        setInitialCandles(null);
                        setInitialVolume(null);
                        setBotTrades([]);
                        setStrategyState(null);
                        setPortfolio(null);
                        return;
                    }
                    
                    const newCandles = tradeData.candles || [];
                    const newVolumes = tradeData.volumes || [];
                    
                    // Only set candles if we have valid data, otherwise set null to show loading
                    setInitialCandles(newCandles.length > 0 ? newCandles : null);
                    setInitialVolume(newVolumes.length > 0 ? newVolumes : null);
                    setActiveTokenInfo(tradeData.token_info);
                    setBotTrades(tradeData.bot_trades || []);
                    setStrategyState(tradeData.strategy_state || null);
                    setPortfolio(tradeData.portfolio || null);
                    
                    // Mark as bootstrapped if we got data
                    if (newCandles.length > 0) {
                        chartBootstrappedRef.current = true;
                    }
                    break;
                case 'TRADE_SUMMARY_UPDATE':
                    setTradeSummaries(message.data.summaries);
                    break;
                case 'UPDATE':
                    // If this is the first candle after NEW_TRADE_STARTING with empty data, initialize the chart
                    if (message.data.candle) {
                        if (!chartBootstrappedRef.current) {
                            // First candle - use it to bootstrap the chart
                            setInitialCandles([message.data.candle]);
                            if (message.data.volume) {
                                setInitialVolume([message.data.volume]);
                            }
                            chartBootstrappedRef.current = true;
                            // Don't set lastCandle yet - let the chart initialize first
                        } else {
                            // Subsequent candles - update normally
                            setLastCandle(message.data.candle);
                        }
                    }
                    if (message.data.volume && chartBootstrappedRef.current) {
                        setLastVolume(message.data.volume);
                    }
                    if (message.data.portfolio) setPortfolio(message.data.portfolio);
                    if (message.data.strategy_state) setStrategyState(message.data.strategy_state);
                    if (message.data.bot_trade) {
                        setBotTrades(prev => [...prev, message.data.bot_trade]);
                        setMarketTrades(prev => [{ ...message.data.bot_trade, isBot: true }, ...prev]);
                    }
                    if (message.data.market_trade) {
                        setMarketTrades(prev => [message.data.market_trade, ...prev]);
                    }
                    break;
            }
        };

        wsConnection.addEventListener('message', handleMessage);
        return () => {
            wsConnection.removeEventListener('message', handleMessage);
        };
    }, [wsConnection]);

    const tradePnl = portfolio?.trade_pnl ?? 0;
    const pnlColor = tradePnl >= 0 ? 'text-green-400' : 'text-red-400';
    const currentPrice = lastCandle?.close ?? 0;
    const overallPnl = portfolio?.overall_pnl ?? tradeSummaries.reduce((acc, s) => acc + (s.status === 'Finished' ? s.pnl : 0), 0);
    const overallPnlColor = overallPnl >= 0 ? 'text-green-400' : 'text-red-400';
    const overallPnlPercent = (overallPnl / initialCapital) * 100;
    const currentWalletValue = portfolio?.total_value ?? (initialCapital + overallPnl);

    const activeAddress = activeTokenInfo?.address || null;
    const activeSymbol = activeTokenInfo?.symbol || "SYSTEM";
    const isWaitingForFirstToken = !activeAddress || activeAddress === 'MARKET_INDEX';
    const activeTradeStatus = tradeSummaries.find(s => s.token.address === activeAddress)?.status ?? 'Inactive';

    return (
        <div className="bg-gray-900 text-white h-screen font-sans flex flex-col p-4">
            <header className="flex-shrink-0 flex justify-between items-center border-b border-gray-700 pb-3 mb-4">
                <div className="flex items-center gap-3">
                    {activeTokenInfo?.logo_url && !isWaitingForFirstToken && (
                        <img 
                            src={activeTokenInfo.logo_url} 
                            alt={activeSymbol} 
                            className="w-12 h-12 rounded-full"
                            onError={(e) => { e.currentTarget.style.display = 'none'; }}
                        />
                    )}
                    <div>
                        <h1 className="text-2xl font-bold">{activeSymbol} / SOL</h1>
                        <p className="text-sm text-gray-400">Autonomous Trading Bot - Mission Control</p>
                    </div>
                </div>
                <div className="flex items-center gap-x-12">
                    <div className="text-right">
                        <p className="text-sm text-gray-400">Current Price</p>
                        <p className="text-3xl font-mono text-white">{currentPrice > 0 ? currentPrice.toPrecision(6) : '...'}</p>
                    </div>
                    <div className="text-right">
                        <p className="text-sm text-gray-400">Trade P&L</p>
                        <p className={`text-xl font-semibold ${pnlColor}`}>{tradePnl >= 0 ? `+${tradePnl.toFixed(4)}` : tradePnl.toFixed(4)} SOL</p>
                    </div>
                </div>
                <div className="flex items-center space-x-4">
                    <span className="text-sm text-gray-400">Trade Status: <span className="font-semibold text-yellow-400">{activeTradeStatus}</span></span>
                    <div className="flex items-center space-x-2">
                        <div className={`w-3 h-3 rounded-full ${isWsConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                        <span>{isWsConnected ? 'Connected' : 'Disconnected'}</span>
                    </div>
                </div>
            </header>

            <main className="flex-grow flex flex-row gap-4 overflow-hidden">
                <div className="flex flex-col gap-4 w-full max-w-xs">
                    <Card title="Overall Performance">
                        <div className="space-y-2 text-sm">
                            <p>Initial Wallet: <span className="font-mono text-gray-400 float-right">{initialCapital.toFixed(4)} SOL</span></p>
                            <p>Current Value: <span className="font-mono text-white float-right">{currentWalletValue.toFixed(4)} SOL</span></p>
                            <div className="border-t border-gray-700 my-2"></div>
                            <p>Total P&L: <span className={`font-mono float-right ${overallPnlColor}`}>{overallPnl >= 0 ? `+${overallPnl.toFixed(4)}` : overallPnl.toFixed(4)} SOL ({overallPnlPercent.toFixed(2)}%)</span></p>
                        </div>
                    </Card>
                    <Card title="Trade Queue" className="flex-grow min-h-0">
                        <TradeSummaryPanel summaries={tradeSummaries} activeTokenAddress={activeAddress} />
                    </Card>
                </div>

                <div className="flex-grow flex flex-col gap-4">
                    <div className="h-3/5 grid grid-cols-1 lg:grid-cols-4 gap-4">
                        <div className="lg:col-span-1 flex flex-col gap-4">
                            <Card title="Current Position">
                                {portfolio?.positions && activeAddress && portfolio.positions[activeAddress] ? (
                                    <div className="space-y-2 text-sm">
                                        <p>Tokens Held: <span className="font-mono text-white float-right">{portfolio.positions[activeAddress].tokens.toFixed(2)}</span></p>
                                        <p>Avg Cost: <span className="font-mono text-white float-right">{portfolio.positions[activeAddress].cost_basis.toFixed(6)}</span></p>
                                    </div>
                                ) : <p className="text-gray-500">No active position.</p>}
                            </Card>
                            <Card title="Bot Trade Log" className="flex-grow min-h-0">
                                <ul className="space-y-2 overflow-y-auto pr-2 h-full">
                                    {botTrades.map((trade, index) => (
                                        <li key={index} className="text-sm p-2 rounded bg-gray-700/50">
                                            <div className="flex justify-between items-center mb-1">
                                                <span className={`font-semibold ${trade.side === 'BUY' ? 'text-blue-400' : 'text-red-400'}`}>{trade.side}</span>
                                                <span className="text-gray-400 font-mono">@ {trade.price.toFixed(6)}</span>
                                            </div>
                                            <div className="text-white font-mono text-right">{trade.token_amount.toFixed(2)} {activeSymbol ? activeSymbol.replace('COIN','') : ''} <span className="text-gray-500">({trade.sol_amount.toFixed(4)} SOL)</span></div>
                                        </li>
                                    ))}
                                </ul>
                            </Card>
                        </div>
                        <div className="lg:col-span-3 bg-gray-800/50 rounded-lg p-2">
                            {chartError ? (
                                <div className="flex items-center justify-center h-full rounded-lg border border-dashed border-red-500/40 bg-red-900/20 text-center px-6">
                                    <div className="space-y-3 max-w-md">
                                        <div className="text-5xl mb-4">⚠️</div>
                                        <p className="text-lg font-semibold text-red-300">
                                            {chartError === 'PAIR_ADDRESS_NOT_FOUND' ? 'Pair Address Not Found' : 'OHLCV Data Unavailable'}
                                        </p>
                                        <p className="text-sm text-gray-400">
                                            {chartError === 'PAIR_ADDRESS_NOT_FOUND' 
                                                ? 'Unable to locate trading pair information for this token. The token may not be listed on supported DEXs.'
                                                : 'Failed to fetch OHLCV data for this token. Please check network connectivity or try another token.'}
                                        </p>
                                    </div>
                                </div>
                            ) : isWaitingForFirstToken ? (
                                <div className="flex items-center justify-center h-full rounded-lg border border-dashed border-indigo-500/40 bg-slate-800/60 text-center px-6">
                                    <div className="space-y-3 max-w-md">
                                        <p className="text-lg font-semibold text-indigo-200">Awaiting first token signal</p>
                                        <p className="text-sm text-gray-400">We’ll light up the chart as soon as a screened token passes sentiment and risk checks. Sit tight! signals are on their way.</p>
                                    </div>
                                </div>
                            ) : (initialCandles !== null && initialCandles.length > 0) ? (
                                <CandlestickChart
                                    key={activeAddress || 'market-index'}
                                    initialData={initialCandles}
                                    initialVolume={initialVolume}
                                    update={lastCandle}
                                    volumeUpdate={lastVolume}
                                    botTrades={botTrades}
                                    strategyState={strategyState}
                                />
                            ) : (
                                <div className="flex items-center justify-center h-full">
                                    <div className="text-center">
                                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
                                        <p className="text-gray-400">Loading chart data...</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                    <div className="h-2/5 grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Card title="Live Trade Analysis">
                            <StrategyPanel state={strategyState} currentPrice={currentPrice} />
                        </Card>
                        <Card title="Live Transactions">
                            <TransactionFeed trades={marketTrades} />
                        </Card>
                    </div>
                </div>
            </main>
        </div>
    );
};

// Main App Component with Navigation
const AppContent: React.FC = () => {
    const { isAuthenticated, user, logout } = useWallet();
    const [currentPage, setCurrentPage] = useState<'dashboard' | 'profile'>('dashboard');

    if (!isAuthenticated) {
        return <Login />;
    }

    return (
        <div className="h-screen flex flex-col bg-gray-900">
            {/* Top Navigation Bar */}
            <nav className="bg-slate-800 border-b border-slate-700 px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-6">
                    <h1 className="text-xl font-bold text-white">Auto Trader Bot</h1>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setCurrentPage('dashboard')}
                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                                currentPage === 'dashboard'
                                    ? 'bg-purple-600 text-white'
                                    : 'text-gray-400 hover:text-white hover:bg-slate-700'
                            }`}
                        >
                            Trading Dashboard
                        </button>
                        <button
                            onClick={() => setCurrentPage('profile')}
                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                                currentPage === 'profile'
                                    ? 'bg-purple-600 text-white'
                                    : 'text-gray-400 hover:text-white hover:bg-slate-700'
                            }`}
                        >
                            Profile / Wallet
                        </button>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <div className="text-right">
                        <div className="text-xs text-gray-400">Wallet</div>
                        <div className="text-sm font-mono text-white">
                            {user?.wallet_address.slice(0, 6)}...{user?.wallet_address.slice(-4)}
                        </div>
                    </div>
                    <div className="text-right">
                        <div className="text-xs text-gray-400">Balance</div>
                        <div className="text-sm font-semibold text-green-400">
                            {user?.initial_sol_balance.toFixed(4)} SOL
                        </div>
                    </div>
                    <button
                        onClick={logout}
                        className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
                    >
                        Logout
                    </button>
                </div>
            </nav>

            {/* Page Content */}
            <div className="flex-1 overflow-hidden">
                {currentPage === 'dashboard' ? <TradingDashboard /> : <ProfilePage />}
            </div>
        </div>
    );
};

// Root App Component with Provider
function App() {
    return (
        <WalletProvider>
            <AppContent />
        </WalletProvider>
    );
}

export default App;