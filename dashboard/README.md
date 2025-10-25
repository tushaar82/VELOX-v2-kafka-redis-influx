# VELOX Analytics Dashboard

Professional-grade real-time trading analytics dashboard for the VELOX trading system.

## Features

### 📊 Real-Time Monitoring
- **Live Position Tracking**: Monitor all open positions with real-time P&L updates
- **Price Charts**: Real-time price charts with trailing stop-loss overlay
- **WebSocket Updates**: Sub-second latency for position and price updates
- **System Health**: Live database connectivity and system status monitoring

### 📈 Performance Analytics
- **Strategy Metrics**: Win rate, profit factor, average trade duration per strategy
- **Trade Analysis**: Detailed breakdown of winning and losing trades
- **Exit Reason Tracking**: Understand why trades are closed
- **Symbol Performance**: Performance metrics grouped by trading symbol

### 🔍 Order Verification
- **Order Lifecycle Tracking**: Ensure all orders are properly closed
- **Unclosed Order Detection**: Automatic detection of orders open >24 hours
- **Diagnostic Tools**: Database health checks and connectivity verification

### 💎 Modern UI
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark Mode Ready**: Professional dark theme for extended use
- **Real-Time Alerts**: Toast notifications for important events
- **Interactive Charts**: Zoom, pan, and hover for detailed insights

## Architecture

### Backend (Python)
- **REST API**: FastAPI-based REST API (port 8000)
- **WebSocket Server**: Real-time updates via WebSocket (port 8765)
- **Data Service**: Unified access to InfluxDB, Redis, SQLite

### Frontend (React + TypeScript)
- **React 18**: Modern React with hooks and functional components
- **TypeScript**: Type-safe development
- **Recharts**: Professional charting library
- **TailwindCSS**: Utility-first CSS framework
- **Zustand**: Lightweight state management
- **React Query**: Data fetching and caching

### Data Flow
```
Trading System → Redis/InfluxDB/SQLite
                      ↓
              Data Service Layer
                      ↓
        REST API + WebSocket Server
                      ↓
              React Dashboard
```

## Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- Redis running on localhost:6379
- InfluxDB running on localhost:8086
- SQLite database at `data/velox.db`

### Quick Start

1. **Install Python dependencies**:
```bash
pip install -r requirements-dashboard.txt
```

2. **Install Node.js dependencies**:
```bash
cd dashboard
npm install
```

3. **Start all services**:
```bash
./scripts/start_dashboard.sh
```

The script will start:
- REST API on http://localhost:8000
- WebSocket server on ws://localhost:8765
- React dev server on http://localhost:3000

### Manual Start

**Backend API Server**:
```bash
cd src/dashboard/api
python rest_api.py
```

**WebSocket Server**:
```bash
cd src/dashboard/api
python websocket_server.py
```

**Frontend Dashboard**:
```bash
cd dashboard
npm run dev
```

## Configuration

### Backend Configuration

Edit `src/dashboard/api/data_service.py` to configure database connections:

```python
data_service = DataService(
    influx_url="http://localhost:8086",
    influx_token="my-token",
    influx_org="velox",
    influx_bucket="trading",
    redis_host="localhost",
    redis_port=6379,
    sqlite_path="data/velox.db"
)
```

### Frontend Configuration

Edit `dashboard/vite.config.ts` to configure API endpoints:

```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
    '/ws': {
      target: 'ws://localhost:8765',
      ws: true,
    },
  },
}
```

## Integration with Trading System

### Publishing Real-Time Updates

To enable real-time dashboard updates, integrate the Redis publisher into your trading system:

```python
from src.utils.redis_publisher import get_redis_publisher

publisher = get_redis_publisher()

# Publish position update
publisher.publish_position_update({
    'strategy_id': 'supertrend_simple',
    'symbol': 'ABB',
    'quantity': 10,
    'entry_price': 2500.00,
    'current_price': 2510.00,
    'highest_price': 2515.00,
    'unrealized_pnl': 100.00,
    'unrealized_pnl_pct': 0.4,
    'trailing_sl': 2490.00
})

# Publish trade closure
publisher.publish_trade_closed({
    'trade_id': 'abc123',
    'strategy_id': 'supertrend_simple',
    'symbol': 'ABB',
    'entry_price': 2500.00,
    'exit_price': 2510.00,
    'quantity': 10,
    'pnl': 100.00,
    'pnl_pct': 0.4,
    'exit_reason': 'Trailing SL hit',
    'duration_seconds': 300
})

# Publish price update
publisher.publish_price_update('ABB', 2510.00)

# Publish trailing SL update
publisher.publish_trailing_sl_update(
    trade_id='abc123',
    symbol='ABB',
    current_sl=2490.00,
    current_price=2510.00
)
```

### Updating Position Data in Redis

Use the Redis Position Tracker to maintain position state:

```python
from src.database.redis_position_tracker import RedisPositionTracker

tracker = RedisPositionTracker()

# Update position
tracker.update_position('supertrend_simple', 'ABB', {
    'strategy_id': 'supertrend_simple',
    'symbol': 'ABB',
    'quantity': 10,
    'entry_price': 2500.00,
    'current_price': 2510.00,
    'highest_price': 2515.00,
    'entry_time': datetime.now().isoformat(),
    'unrealized_pnl': 100.00,
    'unrealized_pnl_pct': 0.4,
    'trade_id': 'abc123'
})

# Update trailing SL
tracker.update_trailing_sl('abc123', {
    'current_sl': 2490.00,
    'sl_type': 'ATR',
    'sl_value': 5.5
})

# Remove position when closed
tracker.remove_position('supertrend_simple', 'ABB')
```

## API Reference

### REST API Endpoints

**System Status**
- `GET /health` - Health check
- `GET /api/status` - System status with database connectivity

**Positions**
- `GET /api/positions` - Get all open positions
- `GET /api/positions/{symbol}` - Get position for specific symbol

**Trades**
- `GET /api/trades/closed` - Get closed trades (with limit and filter)
- `GET /api/trades/unclosed` - Get potentially unclosed orders

**Strategies**
- `GET /api/strategies` - Get all strategy metrics
- `GET /api/strategies/{strategy_id}` - Get specific strategy metrics

**Analytics**
- `GET /api/analytics/summary` - Comprehensive analytics summary
- `GET /api/analytics/performance` - Detailed performance analysis

**Diagnostics**
- `GET /api/diagnostics/verify-orders` - Verify order closure
- `GET /api/diagnostics/database-health` - Check database health

### WebSocket Messages

**Client → Server**:
```json
{
  "type": "subscribe_symbol",
  "symbol": "ABB"
}
```

**Server → Client**:
```json
{
  "type": "position_update",
  "data": {
    "strategy_id": "supertrend_simple",
    "symbol": "ABB",
    "current_price": 2510.00,
    "unrealized_pnl": 100.00
  }
}
```

## Dashboard Features

### 1. Open Positions View
- Real-time position cards with live P&L
- Entry price, current price, highest price
- Trailing stop-loss display
- Click to view detailed price chart

### 2. Price Charts
- Real-time price line chart
- Trailing SL overlay
- Entry price and highest price reference lines
- Automatic refresh every 5 seconds

### 3. Closed Trades Table
- Sortable table of all closed trades
- Entry/exit prices, P&L, duration
- Exit reason badges
- Win/loss indicators

### 4. Strategy Metrics
- Win rate circular progress
- Total trades, wins, losses
- Average win/loss amounts
- Profit factor and best streak
- Average trade duration

### 5. Order Verification
- Automatic detection of unclosed orders
- Orders open >24 hours flagged
- Manual refresh button
- Real-time alerts

## Development

### Build for Production

```bash
cd dashboard
npm run build
```

The build output will be in `dashboard/dist/`.

### Linting

```bash
cd dashboard
npm run lint
```

### Type Checking

TypeScript will automatically check types during development. For explicit checks:

```bash
cd dashboard
npx tsc --noEmit
```

## Troubleshooting

### WebSocket Connection Failed
- Ensure WebSocket server is running on port 8765
- Check firewall settings
- Verify WebSocket URL in `vite.config.ts`

### No Data Showing
- Verify database connections (Redis, InfluxDB, SQLite)
- Check backend logs for errors
- Ensure trading system is running and publishing data

### Real-time Updates Not Working
- Check Redis pub/sub is properly integrated
- Verify Redis connection in backend
- Check browser console for WebSocket errors

### API Errors
- Verify REST API is running on port 8000
- Check database connectivity
- Review API logs for specific errors

## Performance

- **WebSocket Latency**: <100ms for position updates
- **Chart Refresh Rate**: 5 seconds (configurable)
- **Position Updates**: Real-time via Redis pub/sub
- **API Response Time**: <50ms for cached data

## Security

⚠️ **Important**: This dashboard is designed for local development and testing.

For production deployment:
1. Add authentication (JWT, OAuth)
2. Enable HTTPS/WSS
3. Configure CORS properly
4. Use environment variables for secrets
5. Add rate limiting
6. Implement access control

## Support

For issues or questions:
- Check logs in `src/dashboard/api/` for backend errors
- Check browser console for frontend errors
- Review database connectivity
- Verify configuration settings

## License

Part of the VELOX trading system.
