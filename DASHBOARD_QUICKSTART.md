# VELOX Analytics Dashboard - Quick Start Guide

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements-dashboard.txt

# Install Node.js dependencies
cd dashboard && npm install && cd ..
```

### Step 2: Start the Dashboard

```bash
# Start all services with one command
./scripts/start_dashboard.sh
```

### Step 3: Access the Dashboard

Open your browser and navigate to:
- **Dashboard**: http://localhost:3000
- **REST API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📊 What You'll See

### Open Positions Tab
- Real-time position cards showing:
  - Current P&L (live updates)
  - Entry price vs current price
  - Trailing stop-loss level
  - Position quantity and duration
- Click any position to see detailed price chart

### Closed Trades Tab
- Complete trade history with:
  - Entry and exit prices
  - P&L and percentage gain/loss
  - Trade duration
  - Exit reason (Trailing SL, Manual close, etc.)

### Strategy Metrics Tab
- Performance cards for each strategy:
  - Win rate circular progress
  - Win/loss breakdown
  - Profit factor
  - Average trade duration
  - Best winning streak

### Order Verification Tab
- Ensures all orders are properly closed
- Detects orders open >24 hours
- Real-time health checks

## 🔧 Integration with Your Trading System

To get real-time updates in the dashboard, add these lines to your trading code:

### 1. Import the Publisher

```python
from src.utils.redis_publisher import get_redis_publisher

publisher = get_redis_publisher()
```

### 2. Publish Position Updates (in your tick handler)

```python
# When position price updates
publisher.publish_position_update({
    'strategy_id': strategy_id,
    'symbol': symbol,
    'quantity': quantity,
    'entry_price': entry_price,
    'current_price': current_price,
    'highest_price': highest_price,
    'unrealized_pnl': pnl,
    'unrealized_pnl_pct': pnl_pct,
    'trailing_sl': trailing_sl,
    'entry_time': entry_time.isoformat()
})
```

### 3. Publish Trade Closures

```python
# When trade closes
publisher.publish_trade_closed({
    'trade_id': trade_id,
    'strategy_id': strategy_id,
    'symbol': symbol,
    'entry_price': entry_price,
    'exit_price': exit_price,
    'quantity': quantity,
    'pnl': pnl,
    'pnl_pct': pnl_pct,
    'exit_reason': exit_reason,
    'entry_time': entry_time.isoformat(),
    'exit_time': exit_time.isoformat(),
    'duration_seconds': duration_seconds
})
```

### 4. Track Positions in Redis (for persistence)

```python
from src.database.redis_position_tracker import RedisPositionTracker

tracker = RedisPositionTracker()

# When position opens
tracker.update_position(strategy_id, symbol, {
    'strategy_id': strategy_id,
    'symbol': symbol,
    'quantity': quantity,
    'entry_price': entry_price,
    'current_price': current_price,
    'highest_price': highest_price,
    'entry_time': entry_time.isoformat(),
    'unrealized_pnl': pnl,
    'unrealized_pnl_pct': pnl_pct,
    'trade_id': trade_id
})

# When trailing SL updates
tracker.update_trailing_sl(trade_id, {
    'current_sl': trailing_sl,
    'sl_type': 'ATR',  # or 'percentage', 'ma', 'time_decay'
    'sl_value': atr_multiplier
})

# When position closes
tracker.remove_position(strategy_id, symbol)
```

## 🎯 Example Integration

Here's a complete example for a strategy:

```python
from src.utils.redis_publisher import get_redis_publisher
from src.database.redis_position_tracker import RedisPositionTracker

class MyStrategy:
    def __init__(self):
        self.publisher = get_redis_publisher()
        self.tracker = RedisPositionTracker()

    def on_tick(self, tick):
        # Update position with current price
        if self.has_position:
            current_price = tick['price']

            # Calculate P&L
            pnl = (current_price - self.entry_price) * self.quantity
            pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100

            # Update highest price
            self.highest_price = max(self.highest_price, current_price)

            # Publish real-time update
            self.publisher.publish_position_update({
                'strategy_id': self.strategy_id,
                'symbol': self.symbol,
                'quantity': self.quantity,
                'entry_price': self.entry_price,
                'current_price': current_price,
                'highest_price': self.highest_price,
                'unrealized_pnl': pnl,
                'unrealized_pnl_pct': pnl_pct,
                'trailing_sl': self.trailing_sl,
                'entry_time': self.entry_time.isoformat()
            })

    def close_position(self, exit_price, exit_reason):
        # Calculate final P&L
        pnl = (exit_price - self.entry_price) * self.quantity
        pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100

        # Publish trade closure
        self.publisher.publish_trade_closed({
            'trade_id': self.trade_id,
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'entry_price': self.entry_price,
            'exit_price': exit_price,
            'quantity': self.quantity,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason,
            'entry_time': self.entry_time.isoformat(),
            'exit_time': datetime.now().isoformat(),
            'duration_seconds': int((datetime.now() - self.entry_time).total_seconds())
        })

        # Remove from Redis
        self.tracker.remove_position(self.strategy_id, self.symbol)
```

## 📱 Dashboard Features

### Real-Time Updates
- Position P&L updates every second
- Price charts refresh every 5 seconds
- WebSocket connection status indicator
- Database health monitoring

### Interactive Charts
- Click any position to view detailed chart
- Price vs Trailing SL overlay
- Entry price and highest price markers
- Hover for exact values

### Smart Alerts
- Trade closed notifications
- Trailing SL updates
- System status changes
- Auto-dismiss after 5 seconds

## 🔍 Debugging Your Strategies

### 1. Check if Indicators are Correct
- View current indicator values in the position cards
- Compare with your strategy calculations
- Verify indicator parameters

### 2. Verify Trailing SL Logic
- See real-time trailing SL on charts
- Monitor how SL tightens with price
- Check SL buffer from current price

### 3. Analyze Exit Reasons
- Group trades by exit reason
- Identify if trailing SL is too tight/loose
- See which indicators trigger exits

### 4. Strategy Performance
- Compare win rates across strategies
- Identify best-performing symbols
- Analyze average trade duration
- Review profit factor and expectancy

## 🐛 Troubleshooting

### Dashboard shows no data
1. Check if trading system is running
2. Verify databases are accessible
3. Check backend logs for errors

### Real-time updates not working
1. Ensure Redis is running (`redis-cli ping`)
2. Verify publisher integration in your code
3. Check WebSocket connection status (top-right indicator)

### Charts not loading
1. Verify InfluxDB is running and accessible
2. Check if historical data exists
3. Review browser console for errors

## 📊 What to Monitor

### During Live Trading
1. **Open Positions** - Watch real-time P&L
2. **Trailing SL** - Ensure it's tightening properly
3. **Order Verification** - Check no orders are stuck

### After Trading Session
1. **Closed Trades** - Review all exit reasons
2. **Strategy Metrics** - Compare strategy performance
3. **Performance Analysis** - Use API analytics endpoints

## 🎓 Next Steps

1. **Customize the Dashboard**
   - Edit React components in `dashboard/src/components/`
   - Modify charts in `PriceChart.tsx`
   - Add new metrics in `StrategyMetricsCard.tsx`

2. **Add More Analytics**
   - Create new API endpoints in `src/dashboard/api/rest_api.py`
   - Add new queries to `DataService`
   - Build new React components

3. **Deploy to Production**
   - Build dashboard: `cd dashboard && npm run build`
   - Add authentication
   - Configure HTTPS/WSS
   - Use environment variables

## 📖 Full Documentation

See `dashboard/README.md` for complete documentation including:
- Architecture details
- API reference
- Advanced configuration
- Production deployment guide

---

**Happy Trading! 🚀**
