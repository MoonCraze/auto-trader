/**
 * API service for interacting with the demo wallet backend
 * Base URL: https://refactored-space-spork-44rgpv564v4f5qg-8080.app.github.dev
 */

const API_BASE_URL = 'https://refactored-space-spork-44rgpv564v4f5qg-8080.app.github.dev';

export interface WalletBalance {
  success: boolean;
  wallet: string;
  balances: Array<{
    mint: string;
    amount: string;
    uiAmount: number;
  }>;
  total: number;
}

export interface BuyRequest {
  tokenAddress: string;
  amount: number;
  slippageBps: number;
}

export interface SellRequest {
  tokenAddress: string;
  amount: number;
  decimals: number;
  slippageBps: number;
}

export interface TradeResponse {
  success: boolean;
  message?: string;
  signature?: string;
  error?: string;
}

/**
 * Fetch wallet balance from demo backend
 * No wallet address needed as it's included in the backend
 */
export async function fetchWalletBalance(): Promise<WalletBalance> {
  const response = await fetch(`${API_BASE_URL}/api/balance`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch balance: ${response.statusText}`);
  }
  
  return await response.json();
}

/**
 * Execute a buy order
 */
export async function executeBuy(request: BuyRequest): Promise<TradeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/buy`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Buy request failed: ${response.statusText}`);
  }
  
  return await response.json();
}

/**
 * Execute a sell order
 */
export async function executeSell(request: SellRequest): Promise<TradeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/sell`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Sell request failed: ${response.statusText}`);
  }
  
  return await response.json();
}
