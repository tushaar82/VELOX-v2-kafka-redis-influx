/**
 * REST API client for dashboard data
 */
import axios from 'axios';
import type { Position, ClosedTrade, StrategyMetrics } from './websocket';

const API_BASE_URL = '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export interface SystemStatus {
  timestamp: string;
  databases: {
    redis: boolean;
    influxdb: boolean;
    sqlite: boolean;
  };
  open_positions_count: number;
  total_pnl: number;
}

export interface AnalyticsSummary {
  summary: {
    open_positions: number;
    total_unrealized_pnl: number;
    total_realized_pnl: number;
    total_pnl: number;
    closed_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: number;
  };
  strategies: Record<string, StrategyMetrics>;
  system_status: SystemStatus;
  timestamp: string;
}

export interface PerformanceAnalysis {
  overall: {
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: number;
    avg_win: number;
    avg_loss: number;
    profit_factor: number;
    expectancy: number;
    total_pnl: number;
  };
  by_symbol: Record<string, {
    trades: number;
    wins: number;
    total_pnl: number;
    win_rate: number;
  }>;
  by_exit_reason: Record<string, {
    count: number;
    total_pnl: number;
  }>;
  timestamp: string;
}

export interface UnclosedOrder {
  trade_id: string;
  strategy_id: string;
  symbol: string;
  entry_time: string;
  entry_price: number;
  quantity: number;
  duration_hours: number;
}

export const api = {
  // Status & Health
  async getStatus(): Promise<SystemStatus> {
    const response = await apiClient.get('/status');
    return response.data;
  },

  async getHealth() {
    const response = await apiClient.get('/health');
    return response.data;
  },

  // Positions
  async getPositions(): Promise<{ count: number; positions: Position[]; timestamp: string }> {
    const response = await apiClient.get('/positions');
    return response.data;
  },

  async getPosition(symbol: string, strategyId?: string): Promise<{ position: Position; timestamp: string }> {
    const params = strategyId ? { strategy_id: strategyId } : {};
    const response = await apiClient.get(`/positions/${symbol}`, { params });
    return response.data;
  },

  // Trades
  async getClosedTrades(limit: number = 100, strategyId?: string): Promise<{ count: number; trades: ClosedTrade[]; timestamp: string }> {
    const params: any = { limit };
    if (strategyId) params.strategy_id = strategyId;

    const response = await apiClient.get('/trades/closed', { params });
    return response.data;
  },

  async getUnclosedOrders(): Promise<{ count: number; unclosed_orders: UnclosedOrder[]; timestamp: string }> {
    const response = await apiClient.get('/trades/unclosed');
    return response.data;
  },

  // Strategies
  async getAllStrategies(): Promise<{ count: number; strategies: Record<string, StrategyMetrics>; timestamp: string }> {
    const response = await apiClient.get('/strategies');
    return response.data;
  },

  async getStrategyMetrics(strategyId: string): Promise<{ strategy: StrategyMetrics; timestamp: string }> {
    const response = await apiClient.get(`/strategies/${strategyId}`);
    return response.data;
  },

  // Price & Indicators
  async getPriceHistory(symbol: string, hours: number = 1) {
    const response = await apiClient.get(`/price/${symbol}`, { params: { hours } });
    return response.data;
  },

  async getIndicators(symbol: string, strategyId: string) {
    const response = await apiClient.get(`/indicators/${symbol}/${strategyId}`);
    return response.data;
  },

  async getTrailingSLHistory(tradeId: string) {
    const response = await apiClient.get(`/trailing-sl/${tradeId}`);
    return response.data;
  },

  // Analytics
  async getAnalyticsSummary(): Promise<AnalyticsSummary> {
    const response = await apiClient.get('/analytics/summary');
    return response.data;
  },

  async getPerformanceAnalysis(): Promise<PerformanceAnalysis> {
    const response = await apiClient.get('/analytics/performance');
    return response.data;
  },

  // Diagnostics
  async verifyOrderClosure() {
    const response = await apiClient.get('/diagnostics/verify-orders');
    return response.data;
  },

  async checkDatabaseHealth() {
    const response = await apiClient.get('/diagnostics/database-health');
    return response.data;
  },
};
