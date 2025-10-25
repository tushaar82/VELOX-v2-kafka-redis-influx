/**
 * Strategy Metrics Card - Performance metrics for each strategy
 */
import React from 'react';
import { BarChart3, TrendingUp, Target, Award } from 'lucide-react';
import type { StrategyMetrics } from '../services/websocket';
import { formatCurrency, formatPercent, formatNumber, formatDuration, truncateStrategyId } from '../utils/formatters';

interface StrategyMetricsCardProps {
  metrics: StrategyMetrics;
}

export const StrategyMetricsCard: React.FC<StrategyMetricsCardProps> = ({ metrics }) => {
  const winRate = metrics.win_rate;
  const isPerforming = winRate >= 50 && metrics.total_pnl > 0;

  return (
    <div className={`bg-white rounded-lg shadow-md p-5 border-t-4 ${
      isPerforming ? 'border-success-500' : 'border-dark-300'
    }`}>
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-bold text-dark-800">{truncateStrategyId(metrics.strategy_id)}</h3>
          <p className="text-sm text-dark-500">{metrics.total_trades} trades executed</p>
        </div>
        <div className={`p-2 rounded-lg ${isPerforming ? 'bg-success-100' : 'bg-dark-100'}`}>
          <BarChart3 className={isPerforming ? 'text-success-600' : 'text-dark-600'} size={24} />
        </div>
      </div>

      {/* Win Rate Circle */}
      <div className="flex items-center justify-center mb-4">
        <div className="relative">
          <svg className="w-32 h-32 transform -rotate-90">
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke="#e2e8f0"
              strokeWidth="8"
              fill="none"
            />
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke={winRate >= 50 ? '#22c55e' : winRate >= 30 ? '#eab308' : '#ef4444'}
              strokeWidth="8"
              fill="none"
              strokeDasharray={`${2 * Math.PI * 56 * (winRate / 100)} ${2 * Math.PI * 56}`}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-bold text-dark-800">{formatNumber(winRate, 1)}%</span>
            <span className="text-xs text-dark-500">Win Rate</span>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="bg-success-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp size={16} className="text-success-600" />
            <span className="text-xs font-medium text-success-900">Wins</span>
          </div>
          <p className="text-xl font-bold text-success-700">{metrics.winning_trades}</p>
          <p className="text-xs text-success-600">Avg: {formatCurrency(metrics.avg_win)}</p>
        </div>

        <div className="bg-danger-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp size={16} className="text-danger-600 transform rotate-180" />
            <span className="text-xs font-medium text-danger-900">Losses</span>
          </div>
          <p className="text-xl font-bold text-danger-700">{metrics.losing_trades}</p>
          <p className="text-xs text-danger-600">Avg: {formatCurrency(metrics.avg_loss)}</p>
        </div>
      </div>

      {/* Additional Metrics */}
      <div className="space-y-2">
        <div className="flex justify-between items-center py-2 border-b border-dark-200">
          <span className="text-sm text-dark-600">Total P&L</span>
          <span className={`font-bold ${metrics.total_pnl >= 0 ? 'text-success-600' : 'text-danger-600'}`}>
            {formatCurrency(metrics.total_pnl)}
          </span>
        </div>

        <div className="flex justify-between items-center py-2 border-b border-dark-200">
          <span className="text-sm text-dark-600">Profit Factor</span>
          <span className="font-semibold text-dark-800">{formatNumber(metrics.profit_factor, 2)}</span>
        </div>

        <div className="flex justify-between items-center py-2 border-b border-dark-200">
          <span className="text-sm text-dark-600">Avg Duration</span>
          <span className="font-semibold text-dark-800">{formatDuration(metrics.avg_trade_duration_minutes)}</span>
        </div>

        <div className="flex justify-between items-center py-2">
          <span className="text-sm text-dark-600">Best Streak</span>
          <div className="flex items-center gap-2">
            <Award size={14} className="text-primary-500" />
            <span className="font-semibold text-dark-800">{metrics.max_consecutive_wins} wins</span>
          </div>
        </div>
      </div>
    </div>
  );
};
