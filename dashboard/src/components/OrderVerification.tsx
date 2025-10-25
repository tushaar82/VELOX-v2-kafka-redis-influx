/**
 * Order Verification Panel - Ensures all orders are properly closed
 */
import React, { useEffect, useState } from 'react';
import { Shield, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import type { UnclosedOrder } from '../services/api';
import { formatDateTime, formatCurrency } from '../utils/formatters';

export const OrderVerification: React.FC = () => {
  const [unclosedOrders, setUnclosedOrders] = useState<UnclosedOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastCheck, setLastCheck] = useState<string>('');

  const checkOrders = async () => {
    try {
      setLoading(true);
      const response = await api.getUnclosedOrders();
      setUnclosedOrders(response.unclosed_orders);
      setLastCheck(new Date().toISOString());
    } catch (error) {
      console.error('Error checking unclosed orders:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkOrders();

    // Check every 30 seconds
    const interval = setInterval(checkOrders, 30000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-white rounded-lg shadow-md p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Shield className={unclosedOrders.length === 0 ? 'text-success-600' : 'text-warning-600'} size={24} />
          <div>
            <h3 className="text-lg font-bold text-dark-800">Order Verification</h3>
            <p className="text-sm text-dark-500">
              Last check: {lastCheck ? formatDateTime(lastCheck) : 'Never'}
            </p>
          </div>
        </div>

        <button
          onClick={checkOrders}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Status */}
      {loading ? (
        <div className="text-center py-8 text-dark-500">Checking orders...</div>
      ) : unclosedOrders.length === 0 ? (
        <div className="flex items-center justify-center gap-3 py-8 bg-success-50 rounded-lg">
          <CheckCircle className="text-success-600" size={32} />
          <div>
            <p className="text-lg font-semibold text-success-800">All Orders Properly Closed</p>
            <p className="text-sm text-success-600">No issues detected</p>
          </div>
        </div>
      ) : (
        <div>
          <div className="flex items-center gap-3 mb-4 p-3 bg-warning-50 rounded-lg">
            <AlertTriangle className="text-warning-600" size={24} />
            <div>
              <p className="font-semibold text-warning-800">
                {unclosedOrders.length} orders may need attention
              </p>
              <p className="text-sm text-warning-600">Orders open for more than 24 hours</p>
            </div>
          </div>

          {/* Unclosed Orders Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-dark-100">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-dark-700">Symbol</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-dark-700">Strategy</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-dark-700">Entry Price</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-dark-700">Quantity</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-dark-700">Entry Time</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-dark-700">Duration (hrs)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-200">
                {unclosedOrders.map((order) => (
                  <tr key={order.trade_id} className="hover:bg-dark-50">
                    <td className="px-3 py-2 font-semibold text-dark-800">{order.symbol}</td>
                    <td className="px-3 py-2 text-sm text-dark-600">{order.strategy_id}</td>
                    <td className="px-3 py-2 text-right text-sm text-dark-700">
                      {formatCurrency(order.entry_price)}
                    </td>
                    <td className="px-3 py-2 text-right text-sm text-dark-700">{order.quantity}</td>
                    <td className="px-3 py-2 text-sm text-dark-600">{formatDateTime(order.entry_time)}</td>
                    <td className="px-3 py-2 text-right font-semibold text-warning-700">
                      {order.duration_hours.toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
