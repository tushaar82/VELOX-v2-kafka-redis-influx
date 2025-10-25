/**
 * Zustand store for dashboard state management
 */
import { create } from 'zustand';
import type { Position, ClosedTrade, StrategyMetrics } from '../services/websocket';

export interface DashboardState {
  // Positions
  positions: Position[];
  setPositions: (positions: Position[]) => void;
  updatePosition: (position: Position) => void;

  // Closed Trades
  closedTrades: ClosedTrade[];
  setClosedTrades: (trades: ClosedTrade[]) => void;
  addClosedTrade: (trade: ClosedTrade) => void;

  // Strategy Metrics
  strategyMetrics: Record<string, StrategyMetrics>;
  setStrategyMetrics: (metrics: Record<string, StrategyMetrics>) => void;

  // System Status
  systemStatus: any;
  setSystemStatus: (status: any) => void;

  // Connection Status
  isConnected: boolean;
  setConnected: (connected: boolean) => void;

  // Selected filters
  selectedStrategy: string | null;
  setSelectedStrategy: (strategy: string | null) => void;

  selectedSymbol: string | null;
  setSelectedSymbol: (symbol: string | null) => void;

  // Alerts
  alerts: Array<{ id: string; type: 'info' | 'success' | 'warning' | 'error'; message: string; timestamp: string }>;
  addAlert: (type: 'info' | 'success' | 'warning' | 'error', message: string) => void;
  removeAlert: (id: string) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  // Positions
  positions: [],
  setPositions: (positions) => set({ positions }),
  updatePosition: (position) =>
    set((state) => {
      const index = state.positions.findIndex(
        (p) => p.symbol === position.symbol && p.strategy_id === position.strategy_id
      );

      if (index >= 0) {
        const newPositions = [...state.positions];
        newPositions[index] = position;
        return { positions: newPositions };
      } else {
        return { positions: [...state.positions, position] };
      }
    }),

  // Closed Trades
  closedTrades: [],
  setClosedTrades: (trades) => set({ closedTrades: trades }),
  addClosedTrade: (trade) =>
    set((state) => ({
      closedTrades: [trade, ...state.closedTrades],
    })),

  // Strategy Metrics
  strategyMetrics: {},
  setStrategyMetrics: (metrics) => set({ strategyMetrics: metrics }),

  // System Status
  systemStatus: null,
  setSystemStatus: (status) => set({ systemStatus: status }),

  // Connection Status
  isConnected: false,
  setConnected: (connected) => set({ isConnected: connected }),

  // Filters
  selectedStrategy: null,
  setSelectedStrategy: (strategy) => set({ selectedStrategy: strategy }),

  selectedSymbol: null,
  setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),

  // Alerts
  alerts: [],
  addAlert: (type, message) =>
    set((state) => ({
      alerts: [
        ...state.alerts,
        {
          id: Date.now().toString(),
          type,
          message,
          timestamp: new Date().toISOString(),
        },
      ],
    })),
  removeAlert: (id) =>
    set((state) => ({
      alerts: state.alerts.filter((alert) => alert.id !== id),
    })),
}));
