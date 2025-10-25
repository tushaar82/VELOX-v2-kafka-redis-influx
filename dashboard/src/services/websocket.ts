/**
 * WebSocket service for real-time dashboard updates
 */

export interface Position {
  strategy_id: string;
  symbol: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  highest_price: number;
  entry_time: string;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  trailing_sl?: number;
  trade_id?: string;
}

export interface ClosedTrade {
  trade_id: string;
  strategy_id: string;
  symbol: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  entry_time: string;
  exit_time: string;
  pnl: number;
  pnl_pct: number;
  exit_reason: string;
  duration_minutes: number;
}

export interface StrategyMetrics {
  strategy_id: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
  avg_trade_duration_minutes: number;
}

export interface PriceUpdate {
  timestamp: string;
  symbol: string;
  price: number;
  trailing_sl?: number;
}

export type WebSocketMessage =
  | { type: 'initial_positions'; data: Position[] }
  | { type: 'initial_closed_trades'; data: ClosedTrade[] }
  | { type: 'initial_strategy_metrics'; data: Record<string, StrategyMetrics> }
  | { type: 'position_update'; data: Position }
  | { type: 'positions_snapshot'; data: Position[]; timestamp: string }
  | { type: 'trade_closed'; data: ClosedTrade }
  | { type: 'price_update'; symbol: string; data: PriceUpdate }
  | { type: 'trailing_sl_update'; data: any }
  | { type: 'system_status'; data: any }
  | { type: 'pong'; timestamp: string };

export type MessageHandler = (message: WebSocketMessage) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectTimeout: number = 1000;
  private maxReconnectTimeout: number = 30000;
  private currentReconnectTimeout: number = 1000;
  private messageHandlers: Set<MessageHandler> = new Set();
  private isIntentionalClose: boolean = false;
  private heartbeatInterval: number | null = null;

  constructor(private url: string = 'ws://localhost:8765/ws') {}

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    this.isIntentionalClose = false;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.currentReconnectTimeout = this.reconnectTimeout;
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.notifyHandlers(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.stopHeartbeat();

        if (!this.isIntentionalClose) {
          this.scheduleReconnect();
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    this.isIntentionalClose = true;
    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private scheduleReconnect(): void {
    console.log(`Reconnecting in ${this.currentReconnectTimeout}ms...`);

    setTimeout(() => {
      this.connect();
      this.currentReconnectTimeout = Math.min(
        this.currentReconnectTimeout * 2,
        this.maxReconnectTimeout
      );
    }, this.currentReconnectTimeout);
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(() => {
      this.send({ type: 'ping' });
    }, 30000); // Ping every 30 seconds
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval !== null) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  send(data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }

  subscribeToSymbol(symbol: string): void {
    this.send({ type: 'subscribe_symbol', symbol });
  }

  unsubscribeFromSymbol(symbol: string): void {
    this.send({ type: 'unsubscribe_symbol', symbol });
  }

  addMessageHandler(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);

    // Return unsubscribe function
    return () => {
      this.messageHandlers.delete(handler);
    };
  }

  private notifyHandlers(message: WebSocketMessage): void {
    this.messageHandlers.forEach((handler) => {
      try {
        handler(message);
      } catch (error) {
        console.error('Error in message handler:', error);
      }
    });
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const websocketService = new WebSocketService();
