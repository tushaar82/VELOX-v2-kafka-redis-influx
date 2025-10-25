/**
 * Position Card - Shows individual position with live P&L
 */
import React from 'react';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import type { Position } from '../services/websocket';
import { formatCurrency, formatPercent, formatTime, getStatusColor } from '../utils/formatters';

interface PositionCardProps {
  position: Position;
  onClick?: () => void;
}

export const PositionCard: React.FC<PositionCardProps> = ({ position, onClick }) => {
  const isProfitable = position.unrealized_pnl > 0;
  const pnlColor = getStatusColor(position.unrealized_pnl);

  return (
    <div
      className={`bg-white rounded-lg shadow-md p-4 border-l-4 ${
        isProfitable ? 'border-success-500' : 'border-danger-500'
      } hover:shadow-lg transition-shadow cursor-pointer`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="text-lg font-bold text-dark-800">{position.symbol}</h3>
          <p className="text-sm text-dark-500">{position.strategy_id.replace(/_/g, ' ').toUpperCase()}</p>
        </div>
        <div className={`flex items-center ${isProfitable ? 'text-success-600' : 'text-danger-600'}`}>
          {isProfitable ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <p className="text-xs text-dark-500">Entry Price</p>
          <p className="text-sm font-semibold text-dark-800">{formatCurrency(position.entry_price)}</p>
        </div>
        <div>
          <p className="text-xs text-dark-500">Current Price</p>
          <p className="text-sm font-semibold text-dark-800">{formatCurrency(position.current_price)}</p>
        </div>
        <div>
          <p className="text-xs text-dark-500">Quantity</p>
          <p className="text-sm font-semibold text-dark-800">{position.quantity}</p>
        </div>
        <div>
          <p className="text-xs text-dark-500">Highest Price</p>
          <p className="text-sm font-semibold text-dark-800">{formatCurrency(position.highest_price)}</p>
        </div>
      </div>

      {/* Trailing SL */}
      {position.trailing_sl && (
        <div className="bg-primary-50 rounded p-2 mb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-primary-600" />
              <span className="text-xs font-medium text-primary-900">Trailing SL</span>
            </div>
            <span className="text-sm font-bold text-primary-700">{formatCurrency(position.trailing_sl)}</span>
          </div>
          <div className="mt-1">
            <div className="text-xs text-primary-600">
              Buffer: {formatCurrency(position.current_price - position.trailing_sl)}
            </div>
          </div>
        </div>
      )}

      {/* P&L Display */}
      <div className={`rounded p-3 ${isProfitable ? 'bg-success-50' : 'bg-danger-50'}`}>
        <div className="flex justify-between items-center">
          <div>
            <p className={`text-2xl font-bold ${pnlColor}`}>
              {formatCurrency(position.unrealized_pnl)}
            </p>
            <p className={`text-sm font-semibold ${pnlColor}`}>
              {formatPercent(position.unrealized_pnl_pct)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-dark-500">Entry Time</p>
            <p className="text-xs font-medium text-dark-700">{formatTime(position.entry_time)}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
