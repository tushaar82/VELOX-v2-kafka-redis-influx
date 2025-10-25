/**
 * Main Dashboard Application
 */
import React, { useEffect, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from './components/Header';
import { AlertBanner } from './components/AlertBanner';
import { PositionCard } from './components/PositionCard';
import { ClosedTradesTable } from './components/ClosedTradesTable';
import { PriceChart } from './components/PriceChart';
import { StrategyMetricsCard } from './components/StrategyMetricsCard';
import { OrderVerification } from './components/OrderVerification';
import { websocketService } from './services/websocket';
import { useDashboardStore } from './store/dashboardStore';
import { TrendingUp, BarChart3, FileText, Shield } from 'lucide-react';

const queryClient = new QueryClient();

function DashboardContent() {
  const {
    positions,
    closedTrades,
    strategyMetrics,
    selectedSymbol,
    setPositions,
    setClosedTrades,
    setStrategyMetrics,
    setSystemStatus,
    setConnected,
    updatePosition,
    addClosedTrade,
    addAlert,
    setSelectedSymbol,
  } = useDashboardStore();

  const [activeTab, setActiveTab] = useState<'positions' | 'trades' | 'strategies' | 'verification'>('positions');

  useEffect(() => {
    // Connect to WebSocket
    websocketService.connect();

    // Add message handler
    const unsubscribe = websocketService.addMessageHandler((message) => {
      switch (message.type) {
        case 'initial_positions':
          setPositions(message.data);
          break;

        case 'initial_closed_trades':
          setClosedTrades(message.data);
          break;

        case 'initial_strategy_metrics':
          setStrategyMetrics(message.data);
          break;

        case 'position_update':
          updatePosition(message.data);
          break;

        case 'positions_snapshot':
          setPositions(message.data);
          break;

        case 'trade_closed':
          addClosedTrade(message.data);
          addAlert('success', `Trade closed: ${message.data.symbol} - ${message.data.exit_reason}`);
          break;

        case 'system_status':
          setSystemStatus(message.data);
          break;

        case 'trailing_sl_update':
          addAlert('info', 'Trailing stop-loss updated');
          break;
      }
    });

    // Monitor connection status
    const connectionInterval = setInterval(() => {
      setConnected(websocketService.isConnected());
    }, 1000);

    return () => {
      unsubscribe();
      clearInterval(connectionInterval);
      websocketService.disconnect();
    };
  }, []);

  const selectedPosition = selectedSymbol
    ? positions.find((p) => p.symbol === selectedSymbol)
    : null;

  return (
    <div className="min-h-screen bg-dark-50">
      <Header />
      <AlertBanner />

      <main className="container mx-auto px-6 py-6">
        {/* Navigation Tabs */}
        <div className="flex gap-2 mb-6 border-b border-dark-200">
          <button
            onClick={() => setActiveTab('positions')}
            className={`flex items-center gap-2 px-4 py-3 font-medium transition-colors ${
              activeTab === 'positions'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-dark-600 hover:text-primary-600'
            }`}
          >
            <TrendingUp size={20} />
            Open Positions ({positions.length})
          </button>

          <button
            onClick={() => setActiveTab('trades')}
            className={`flex items-center gap-2 px-4 py-3 font-medium transition-colors ${
              activeTab === 'trades'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-dark-600 hover:text-primary-600'
            }`}
          >
            <FileText size={20} />
            Closed Trades ({closedTrades.length})
          </button>

          <button
            onClick={() => setActiveTab('strategies')}
            className={`flex items-center gap-2 px-4 py-3 font-medium transition-colors ${
              activeTab === 'strategies'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-dark-600 hover:text-primary-600'
            }`}
          >
            <BarChart3 size={20} />
            Strategy Metrics ({Object.keys(strategyMetrics).length})
          </button>

          <button
            onClick={() => setActiveTab('verification')}
            className={`flex items-center gap-2 px-4 py-3 font-medium transition-colors ${
              activeTab === 'verification'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-dark-600 hover:text-primary-600'
            }`}
          >
            <Shield size={20} />
            Order Verification
          </button>
        </div>

        {/* Positions Tab */}
        {activeTab === 'positions' && (
          <div className="space-y-6">
            {positions.length === 0 ? (
              <div className="text-center py-16">
                <TrendingUp size={48} className="mx-auto text-dark-400 mb-4" />
                <p className="text-xl text-dark-600">No open positions</p>
                <p className="text-sm text-dark-500 mt-2">Positions will appear here when trades are opened</p>
              </div>
            ) : (
              <>
                {/* Price Chart for Selected Symbol */}
                {selectedPosition && (
                  <div className="mb-6">
                    <PriceChart symbol={selectedPosition.symbol} position={selectedPosition} />
                  </div>
                )}

                {/* Positions Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {positions.map((position) => (
                    <PositionCard
                      key={`${position.strategy_id}-${position.symbol}`}
                      position={position}
                      onClick={() => setSelectedSymbol(position.symbol)}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {/* Closed Trades Tab */}
        {activeTab === 'trades' && (
          <div>
            <ClosedTradesTable trades={closedTrades} limit={100} />
          </div>
        )}

        {/* Strategy Metrics Tab */}
        {activeTab === 'strategies' && (
          <div className="space-y-6">
            {Object.keys(strategyMetrics).length === 0 ? (
              <div className="text-center py-16">
                <BarChart3 size={48} className="mx-auto text-dark-400 mb-4" />
                <p className="text-xl text-dark-600">No strategy metrics available</p>
                <p className="text-sm text-dark-500 mt-2">Metrics will appear after trades are closed</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {Object.values(strategyMetrics).map((metrics) => (
                  <StrategyMetricsCard key={metrics.strategy_id} metrics={metrics} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Order Verification Tab */}
        {activeTab === 'verification' && (
          <div>
            <OrderVerification />
          </div>
        )}
      </main>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <DashboardContent />
    </QueryClientProvider>
  );
}

export default App;
