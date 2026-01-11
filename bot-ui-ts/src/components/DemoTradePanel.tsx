import React, { useState } from 'react';
import { useWallet } from '../context/WalletContext';
import Card from './Card';

/**
 * Demo Trade Panel - Allows manual buy/sell operations using the demo API
 */
const DemoTradePanel: React.FC = () => {
  const { performBuy, performSell, refreshBalance } = useWallet();
  const [tokenAddress, setTokenAddress] = useState('6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN'); // Default example
  const [amount, setAmount] = useState('0.001');
  const [decimals, setDecimals] = useState('6');
  const [slippageBps, setSlippageBps] = useState('100');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleBuy = async () => {
    setIsLoading(true);
    setResult(null);
    setError(null);
    
    try {
      const response = await performBuy({
        tokenAddress,
        amount: parseFloat(amount),
        slippageBps: parseInt(slippageBps),
      });
      
      if (response.success) {
        setResult(`✅ Buy successful! Signature: ${response.signature || 'N/A'}`);
        await refreshBalance();
      } else {
        setError(`❌ Buy failed: ${response.error || response.message || 'Unknown error'}`);
      }
    } catch (err: any) {
      setError(`❌ Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSell = async () => {
    setIsLoading(true);
    setResult(null);
    setError(null);
    
    try {
      const response = await performSell({
        tokenAddress,
        amount: parseFloat(amount),
        decimals: parseInt(decimals),
        slippageBps: parseInt(slippageBps),
      });
      
      if (response.success) {
        setResult(`✅ Sell successful! Signature: ${response.signature || 'N/A'}`);
        await refreshBalance();
      } else {
        setError(`❌ Sell failed: ${response.error || response.message || 'Unknown error'}`);
      }
    } catch (err: any) {
      setError(`❌ Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card title="Demo Trade Panel">
      <div className="space-y-3 text-sm">
        <div>
          <label className="block text-gray-400 mb-1">Token Address</label>
          <input
            type="text"
            value={tokenAddress}
            onChange={(e) => setTokenAddress(e.target.value)}
            className="w-full bg-gray-700 text-white px-3 py-2 rounded border border-gray-600 focus:border-purple-500 focus:outline-none font-mono text-xs"
            placeholder="Token address"
          />
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="block text-gray-400 mb-1">Amount</label>
            <input
              type="text"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full bg-gray-700 text-white px-3 py-2 rounded border border-gray-600 focus:border-purple-500 focus:outline-none"
              placeholder="0.001"
            />
          </div>

          <div>
            <label className="block text-gray-400 mb-1">Decimals</label>
            <input
              type="text"
              value={decimals}
              onChange={(e) => setDecimals(e.target.value)}
              className="w-full bg-gray-700 text-white px-3 py-2 rounded border border-gray-600 focus:border-purple-500 focus:outline-none"
              placeholder="6"
            />
          </div>

          <div>
            <label className="block text-gray-400 mb-1">Slippage (bps)</label>
            <input
              type="text"
              value={slippageBps}
              onChange={(e) => setSlippageBps(e.target.value)}
              className="w-full bg-gray-700 text-white px-3 py-2 rounded border border-gray-600 focus:border-purple-500 focus:outline-none"
              placeholder="100"
            />
          </div>
        </div>

        <div className="flex gap-2 pt-2">
          <button
            onClick={handleBuy}
            disabled={isLoading}
            className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white font-semibold py-2 px-4 rounded transition-colors"
          >
            {isLoading ? 'Processing...' : 'BUY'}
          </button>
          <button
            onClick={handleSell}
            disabled={isLoading}
            className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 text-white font-semibold py-2 px-4 rounded transition-colors"
          >
            {isLoading ? 'Processing...' : 'SELL'}
          </button>
        </div>

        {result && (
          <div className="mt-3 p-2 bg-green-900/30 border border-green-600 rounded text-green-300 text-xs break-all">
            {result}
          </div>
        )}

        {error && (
          <div className="mt-3 p-2 bg-red-900/30 border border-red-600 rounded text-red-300 text-xs break-all">
            {error}
          </div>
        )}
      </div>
    </Card>
  );
};

export default DemoTradePanel;
