import React, { useState, useEffect } from 'react';
import { useWallet } from '../context/WalletContext';
import type { OverallAnalytics, TokenAnalytics, HistoricalTrade } from '../types';
import moment from 'moment-timezone';

const API_BASE = 'http://localhost:8000';

const ProfilePage: React.FC = () => {
  const { user, walletAddress } = useWallet();
  const [overallAnalytics, setOverallAnalytics] = useState<OverallAnalytics | null>(null);
  const [tokenAnalytics, setTokenAnalytics] = useState<TokenAnalytics[]>([]);
  const [recentTrades, setRecentTrades] = useState<HistoricalTrade[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'tokens' | 'history'>('overview');

  useEffect(() => {
    if (walletAddress) {
      fetchAnalytics();
    }
  }, [walletAddress]);

  const fetchAnalytics = async () => {
    if (!walletAddress) return;
    
    setIsLoading(true);
    try {
      const [overallRes, tokensRes, tradesRes] = await Promise.all([
        fetch(`${API_BASE}/api/analytics/${walletAddress}/overall`),
        fetch(`${API_BASE}/api/analytics/${walletAddress}/by-token`),
        fetch(`${API_BASE}/api/trades/${walletAddress}?limit=50`),
      ]);

      if (overallRes.ok) {
        setOverallAnalytics(await overallRes.json());
      }
      if (tokensRes.ok) {
        setTokenAnalytics(await tokensRes.json());
      }
      if (tradesRes.ok) {
        setRecentTrades(await tradesRes.json());
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatSol = (amount: number) => {
    return `${amount >= 0 ? '+' : ''}${amount.toFixed(4)} SOL`;
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const formatDate = (dateString: string) => {
    return moment(dateString).tz('Asia/Colombo').format('MMM DD, YYYY HH:mm:ss');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Wallet Profile</h1>
        <div className="flex items-center gap-4 text-gray-400">
          <span className="font-mono text-sm">{walletAddress?.slice(0, 8)}...{walletAddress?.slice(-8)}</span>
          <span>•</span>
          <span>Initial Balance: {user?.initial_sol_balance.toFixed(4)} SOL</span>
          <span>•</span>
          <span>Joined: {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-slate-700">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-6 py-3 font-semibold transition-colors ${
            activeTab === 'overview'
              ? 'text-purple-400 border-b-2 border-purple-400'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab('tokens')}
          className={`px-6 py-3 font-semibold transition-colors ${
            activeTab === 'tokens'
              ? 'text-purple-400 border-b-2 border-purple-400'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Per-Token Stats
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`px-6 py-3 font-semibold transition-colors ${
            activeTab === 'history'
              ? 'text-purple-400 border-b-2 border-purple-400'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Trade History
        </button>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && overallAnalytics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="text-gray-400 text-sm mb-1">Total P&L</div>
            <div className={`text-2xl font-bold ${overallAnalytics.total_pnl_sol >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatSol(overallAnalytics.total_pnl_sol)}
            </div>
          </div>
          
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="text-gray-400 text-sm mb-1">Win Rate</div>
            <div className={`text-2xl font-bold ${overallAnalytics.win_rate >= 50 ? 'text-green-400' : 'text-yellow-400'}`}>
              {overallAnalytics.win_rate.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {overallAnalytics.total_wins}W / {overallAnalytics.total_losses}L
            </div>
          </div>
          
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="text-gray-400 text-sm mb-1">Total Trades</div>
            <div className="text-2xl font-bold">{overallAnalytics.total_trades}</div>
            <div className="text-xs text-gray-500 mt-1">
              {overallAnalytics.active_trades} active • {overallAnalytics.finished_trades} finished
            </div>
          </div>
          
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="text-gray-400 text-sm mb-1">Trading Volume</div>
            <div className="text-2xl font-bold">{overallAnalytics.total_volume_sol.toFixed(2)} SOL</div>
            <div className="text-xs text-gray-500 mt-1">
              Avg: {overallAnalytics.avg_trade_size_sol.toFixed(2)} SOL
            </div>
          </div>
          
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="text-gray-400 text-sm mb-1">Avg P&L per Trade</div>
            <div className={`text-2xl font-bold ${overallAnalytics.avg_pnl_per_trade >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatSol(overallAnalytics.avg_pnl_per_trade)}
            </div>
          </div>
          
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="text-gray-400 text-sm mb-1">Largest Win</div>
            <div className="text-2xl font-bold text-green-400">
              {formatSol(overallAnalytics.largest_win)}
            </div>
          </div>
          
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="text-gray-400 text-sm mb-1">Largest Loss</div>
            <div className="text-2xl font-bold text-red-400">
              {formatSol(overallAnalytics.largest_loss)}
            </div>
          </div>
          
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="text-gray-400 text-sm mb-1">Unique Tokens</div>
            <div className="text-2xl font-bold">{overallAnalytics.unique_tokens_traded}</div>
          </div>
        </div>
      )}

      {/* Per-Token Tab */}
      {activeTab === 'tokens' && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Token</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Trades</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Win Rate</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Invested</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Returned</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Net P&L</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Avg P&L %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {tokenAnalytics.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-gray-400">
                      No token trading history yet
                    </td>
                  </tr>
                ) : (
                  tokenAnalytics.map((token) => (
                    <tr key={token.token_address} className="hover:bg-slate-700/50">
                      <td className="px-6 py-4">
                        <div className="font-medium">{token.token_symbol}</div>
                        <div className="text-xs text-gray-500 font-mono">{token.token_address.slice(0, 8)}...</div>
                      </td>
                      <td className="px-6 py-4 text-right">{token.total_trades}</td>
                      <td className="px-6 py-4 text-right">
                        <span className={token.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}>
                          {token.win_rate.toFixed(1)}%
                        </span>
                        <div className="text-xs text-gray-500">{token.wins}W/{token.losses}L</div>
                      </td>
                      <td className="px-6 py-4 text-right">{token.total_invested.toFixed(4)}</td>
                      <td className="px-6 py-4 text-right">{token.total_returned.toFixed(4)}</td>
                      <td className={`px-6 py-4 text-right font-semibold ${token.net_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatSol(token.net_pnl)}
                      </td>
                      <td className={`px-6 py-4 text-right ${token.avg_pnl_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatPercent(token.avg_pnl_percent)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Trade History Tab */}
      {activeTab === 'history' && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Token</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Entry</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Exit</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Invested</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">P&L</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">P&L %</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {recentTrades.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-8 text-center text-gray-400">
                      No trade history yet
                    </td>
                  </tr>
                ) : (
                  recentTrades.map((trade) => (
                    <tr key={trade.id} className="hover:bg-slate-700/50">
                      <td className="px-6 py-4">
                        <div className="font-medium">{trade.token_symbol}</div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          trade.status === 'finished' ? 'bg-blue-500/20 text-blue-400' :
                          trade.status === 'active' ? 'bg-green-500/20 text-green-400' :
                          'bg-red-500/20 text-red-400'
                        }`}>
                          {trade.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right text-sm">${trade.entry_price.toFixed(6)}</td>
                      <td className="px-6 py-4 text-right text-sm">
                        {trade.exit_price ? `$${trade.exit_price.toFixed(6)}` : '-'}
                      </td>
                      <td className="px-6 py-4 text-right">{trade.sol_invested.toFixed(4)}</td>
                      <td className={`px-6 py-4 text-right font-semibold ${
                        !trade.pnl_sol ? 'text-gray-400' :
                        trade.pnl_sol >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {trade.pnl_sol !== null ? formatSol(trade.pnl_sol) : '-'}
                      </td>
                      <td className={`px-6 py-4 text-right ${
                        !trade.pnl_percent ? 'text-gray-400' :
                        trade.pnl_percent >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {trade.pnl_percent !== null ? formatPercent(trade.pnl_percent) : '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-400">
                        {formatDate(trade.entry_time)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfilePage;
