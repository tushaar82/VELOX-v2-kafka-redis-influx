/**
 * Dashboard Header with system status
 */
import React from 'react';
import { Activity, Database, Wifi, WifiOff } from 'lucide-react';
import { useDashboardStore } from '../store/dashboardStore';
import { formatCurrency } from '../utils/formatters';

export const Header: React.FC = () => {
  const { isConnected, systemStatus, positions } = useDashboardStore();

  const totalPnL = positions.reduce((sum, pos) => sum + pos.unrealized_pnl, 0);

  return (
    <header className="bg-dark-900 text-white shadow-lg">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <Activity size={32} className="text-primary-400" />
            <div>
              <h1 className="text-2xl font-bold">VELOX Analytics</h1>
              <p className="text-sm text-dark-400">Professional Trading Dashboard</p>
            </div>
          </div>

          {/* Status Indicators */}
          <div className="flex items-center gap-6">
            {/* Total P&L */}
            <div className="text-right">
              <p className="text-xs text-dark-400">Total Unrealized P&L</p>
              <p className={`text-xl font-bold ${totalPnL >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                {formatCurrency(totalPnL)}
              </p>
            </div>

            {/* Open Positions */}
            <div className="text-right">
              <p className="text-xs text-dark-400">Open Positions</p>
              <p className="text-xl font-bold">{positions.length}</p>
            </div>

            {/* Connection Status */}
            <div className="flex items-center gap-2">
              {isConnected ? (
                <>
                  <Wifi className="text-success-400" size={20} />
                  <span className="text-sm text-success-400">Connected</span>
                </>
              ) : (
                <>
                  <WifiOff className="text-danger-400" size={20} />
                  <span className="text-sm text-danger-400">Disconnected</span>
                </>
              )}
            </div>

            {/* Database Status */}
            {systemStatus && (
              <div className="flex items-center gap-2">
                <Database
                  className={
                    Object.values(systemStatus.databases).every(Boolean)
                      ? 'text-success-400'
                      : 'text-danger-400'
                  }
                  size={20}
                />
                <span className="text-xs text-dark-400">
                  {Object.values(systemStatus.databases).filter(Boolean).length}/3 DB
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
