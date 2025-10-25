/**
 * Closed Trades Table - Shows historical trades with exit reasons
 */
import React from 'react';
import { CheckCircle, XCircle, Clock } from 'lucide-react';
import type { ClosedTrade } from '../services/websocket';
import { formatCurrency, formatPercent, formatDateTime, formatDuration, getStatusColor } from '../utils/formatters';

interface ClosedTradesTableProps {
  trades: ClosedTrade[];
  limit?: number;
}

export const ClosedTradesTable: React.FC<ClosedTradesTableProps> = ({ trades, limit = 50 }) => {
  const displayTrades = limit ? trades.slice(0, limit) : trades;

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-dark-800 text-white">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase">Symbol</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase">Strategy</th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase">Entry</th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase">Exit</th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase">Qty</th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase">P&L</th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase">%</th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase">Duration</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase">Exit Reason</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-200">
            {displayTrades.length === 0 ? (
              <tr>
                <td colSpan={10} className="px-4 py-8 text-center text-dark-500">
                  No closed trades yet
                </td>
              </tr>
            ) : (
              displayTrades.map((trade) => {
                const isProfitable = trade.pnl > 0;
                const pnlColor = getStatusColor(trade.pnl);

                return (
                  <tr key={trade.trade_id} className="hover:bg-dark-50 transition-colors">
                    <td className="px-4 py-3">
                      <span className="font-semibold text-dark-800">{trade.symbol}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-dark-600">
                        {trade.strategy_id.replace(/_/g, ' ').substring(0, 20)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-sm text-dark-700">{formatCurrency(trade.entry_price)}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-sm text-dark-700">{formatCurrency(trade.exit_price)}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-sm text-dark-700">{trade.quantity}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {isProfitable ? (
                          <CheckCircle size={14} className="text-success-500" />
                        ) : (
                          <XCircle size={14} className="text-danger-500" />
                        )}
                        <span className={`font-semibold ${pnlColor}`}>
                          {formatCurrency(trade.pnl)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`font-semibold ${pnlColor}`}>
                        {formatPercent(trade.pnl_pct)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <Clock size={12} className="text-dark-400" />
                        <span className="text-xs text-dark-600">
                          {formatDuration(trade.duration_minutes)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-block px-2 py-1 text-xs font-medium bg-primary-100 text-primary-800 rounded">
                        {trade.exit_reason}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-dark-500">{formatDateTime(trade.exit_time)}</span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {trades.length > limit && (
        <div className="bg-dark-50 px-4 py-3 text-center border-t border-dark-200">
          <span className="text-sm text-dark-600">
            Showing {limit} of {trades.length} trades
          </span>
        </div>
      )}
    </div>
  );
};
