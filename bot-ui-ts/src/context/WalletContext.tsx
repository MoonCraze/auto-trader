import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import type { User, AuthState, WalletBalance } from '../types';
import { fetchWalletBalance, executeBuy, executeSell, BuyRequest, SellRequest, TradeResponse } from '../services/api';

interface WalletContextType extends AuthState {
  login: (walletAddress: string) => Promise<void>;
  register: () => Promise<void>;
  logout: () => void;
  wsConnection: WebSocket | null;
  isWsConnected: boolean;
  refreshBalance: () => Promise<void>;
  performBuy: (request: BuyRequest) => Promise<TradeResponse>;
  performSell: (request: SellRequest) => Promise<TradeResponse>;
}

const WalletContext = createContext<WalletContextType | undefined>(undefined);

export const useWallet = () => {
  const context = useContext(WalletContext);
  if (!context) {
    throw new Error('useWallet must be used within WalletProvider');
  }
  return context;
};

interface WalletProviderProps {
  children: ReactNode;
}

const API_BASE = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8765';

export const WalletProvider: React.FC<WalletProviderProps> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    walletAddress: null,
    walletBalance: null,
  });
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);
  const [isWsConnected, setIsWsConnected] = useState(false);

  // Load saved wallet from localStorage on mount
  useEffect(() => {
    const savedWallet = localStorage.getItem('wallet_address');
    if (savedWallet) {
      fetchUserData(savedWallet).then(user => {
        if (user) {
          setAuthState({
            isAuthenticated: true,
            user,
            walletAddress: savedWallet,
            walletBalance: null,
          });
          connectWebSocket(savedWallet);
          // Fetch initial balance
          refreshBalanceInternal();
        }
      });
    }
  }, []);

  // Refresh balance periodically
  useEffect(() => {
    if (authState.isAuthenticated) {
      const interval = setInterval(() => {
        refreshBalanceInternal();
      }, 30000); // Refresh every 30 seconds
      
      return () => clearInterval(interval);
    }
  }, [authState.isAuthenticated]);

  const refreshBalanceInternal = async () => {
    try {
      const balance = await fetchWalletBalance();
      
      // Find SOL balance in the response
      const solBalance = balance.balances.find(b => b.mint === 'SOL');
      const currentBalance = solBalance?.uiAmount ?? 0;
      
      setAuthState(prev => {
        // Store initial balance from API on first fetch (if not already stored)
        let initialBalanceFromApi = prev.user?.initial_balance_from_api;
        if (!initialBalanceFromApi && prev.walletAddress) {
          const storedInitial = localStorage.getItem(`initial_balance_${prev.walletAddress}`);
          if (!storedInitial) {
            // First time fetching - store this as initial balance
            initialBalanceFromApi = currentBalance;
            localStorage.setItem(`initial_balance_${prev.walletAddress}`, currentBalance.toString());
          } else {
            initialBalanceFromApi = parseFloat(storedInitial);
          }
        }
        
        return {
          ...prev,
          walletBalance: balance,
          user: prev.user ? {
            ...prev.user,
            current_balance: currentBalance,
            initial_balance_from_api: initialBalanceFromApi,
          } : null,
        };
      });
    } catch (error) {
      console.error('Failed to fetch balance:', error);
    }
  };

  const refreshBalance = async () => {
    await refreshBalanceInternal();
  };

  const fetchUserData = async (walletAddress: string): Promise<User | null> => {
    try {
      const response = await fetch(`${API_BASE}/api/user/${walletAddress}`);
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Failed to fetch user data:', error);
    }
    return null;
  };

  const connectWebSocket = (walletAddress: string) => {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('WebSocket connected, sending AUTH...');
      ws.send(JSON.stringify({
        type: 'AUTH',
        wallet_address: walletAddress,
      }));
      setIsWsConnected(true);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'AUTH_SUCCESS') {
        console.log('✅ WebSocket authenticated successfully');
      } else if (message.type === 'ERROR') {
        console.error('WebSocket error:', message.message);
        ws.close();
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsWsConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsWsConnected(false);
      // Attempt reconnection after delay
      setTimeout(() => {
        if (authState.walletAddress) {
          connectWebSocket(authState.walletAddress);
        }
      }, 5000);
    };

    setWsConnection(ws);
  };

  const login = async (walletAddress: string) => {
    try {
      const user = await fetchUserData(walletAddress);
      if (user) {
        setAuthState({
          isAuthenticated: true,
          user,
          walletAddress,
          walletBalance: null,
        });
        localStorage.setItem('wallet_address', walletAddress);
        connectWebSocket(walletAddress);
        // Fetch initial balance
        await refreshBalanceInternal();
      } else {
        throw new Error('Invalid wallet address');
      }
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const register = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/register`, {
        method: 'POST',
      });
      
      if (response.ok) {
        const data = await response.json();
        const user: User = {
          wallet_address: data.wallet_address,
          initial_sol_balance: data.initial_sol_balance,
          created_at: data.created_at,
        };
        
        setAuthState({
          isAuthenticated: true,
          user,
          walletAddress: data.wallet_address,
          walletBalance: null,
        });
        localStorage.setItem('wallet_address', data.wallet_address);
        connectWebSocket(data.wallet_address);
        // Fetch initial balance
        await refreshBalanceInternal();
      } else {
        throw new Error('Registration failed');
      }
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  };

  const performBuy = async (request: BuyRequest): Promise<TradeResponse> => {
    try {
      const result = await executeBuy(request);
      // Refresh balance after trade
      await refreshBalanceInternal();
      return result;
    } catch (error) {
      console.error('Buy failed:', error);
      throw error;
    }
  };

  const performSell = async (request: SellRequest): Promise<TradeResponse> => {
    try {
      const result = await executeSell(request);
      // Refresh balance after trade
      await refreshBalanceInternal();
      return result;
    } catch (error) {
      console.error('Sell failed:', error);
      throw error;
    }
  };

  const logout = () => {
    if (wsConnection) {
      wsConnection.close();
    }
    setAuthState({
      isAuthenticated: false,
      user: null,
      walletAddress: null,
      walletBalance: null,
    });
    setWsConnection(null);
    setIsWsConnected(false);
    localStorage.removeItem('wallet_address');
  };

  return (
    <WalletContext.Provider
      value={{
        ...authState,
        login,
        register,
        logout,
        wsConnection,
        isWsConnected,
        refreshBalance,
        performBuy,
        performSell,
      }}
    >
      {children}
    </WalletContext.Provider>
  );
};
