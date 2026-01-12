import type { Time } from 'lightweight-charts';

export interface Candle {
  time: Time;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface BotTrade {
    time: Time;
    side: 'BUY' | 'SELL';
    price: number;
    sol_amount: number;
    token_amount: number;
}

export interface MarketTrade {
    side: 'BUY' | 'SELL';
    sol_amount: number;
    price: number;
    timestamp: string;
    isBot?: boolean;
}

export interface Position {
    tokens: number;
    cost_basis: number;
}

export interface Portfolio {
    sol_balance: number;
    total_value: number;
    trade_pnl: number;
    overall_pnl: number;
    positions: Record<string, Position>;
}

export interface VolumeData {
  time: Time;
  value: number;
  color: string;
}

export interface TokenInfo {
    address: string;
    symbol: string;
    logo_url?: string;
}

export interface TwitterDetails {
  pos: number;
  neg: number;
  total: number;
  pos_pct: number;
  neg_pct: number;
  shrunk_sentiment: number;
}

export interface SentimentText {
  text: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  color: string;
}

export interface SentimentData {
  score: number;
  twitter_details?: TwitterDetails;
  twitter_texts?: string[];
  sample_texts?: SentimentText[];
}

export interface TradeSummary {
  token: TokenInfo;
  status: 'Pending' | 'Screening' | 'Monitoring' | 'Active' | 'Finished' | 'Failed';
  pnl: number;
  sentiment_score: number | null;
  mention_count: number | null;
  sentiment_data?: SentimentData;
}


export interface StrategyState {
    entry_price: number;
    stop_loss_price: number;
    take_profit_tiers: [number, number][];
    highest_price_seen: number;
}

// Authentication & User Types
export interface User {
    wallet_address: string;
    initial_sol_balance: number;
    created_at: string;
}

export interface AuthState {
    isAuthenticated: boolean;
    user: User | null;
    walletAddress: string | null;
}

// Historical Trade Types
export interface HistoricalTrade {
    id: number;
    token_symbol: string;
    token_address: string;
    status: 'active' | 'finished' | 'failed';
    entry_time: string;
    entry_price: number;
    quantity: number;
    sol_invested: number;
    exit_time: string | null;
    exit_price: number | null;
    sol_returned: number | null;
    pnl_sol: number | null;
    pnl_percent: number | null;
    exit_reason: string | null;
}

// Analytics Types
export interface TokenAnalytics {
    token_symbol: string;
    token_address: string;
    total_trades: number;
    wins: number;
    losses: number;
    win_rate: number;
    total_invested: number;
    total_returned: number;
    net_pnl: number;
    avg_pnl_percent: number;
    best_trade_pnl: number;
    worst_trade_pnl: number;
}

export interface OverallAnalytics {
    total_trades: number;
    active_trades: number;
    finished_trades: number;
    total_wins: number;
    total_losses: number;
    win_rate: number;
    total_volume_sol: number;
    total_pnl_sol: number;
    avg_trade_size_sol: number;
    avg_pnl_per_trade: number;
    largest_win: number;
    largest_loss: number;
    unique_tokens_traded: number;
}