# VELOX Dashboard Guide

## 🌐 Running the Dashboard

### Quick Start:
```bash
# Run system with live dashboard
python run_with_dashboard.py --date 2020-09-15 --speed 100

# Then open in your browser:
http://localhost:5000
```

### Command Options:
```bash
python run_with_dashboard.py \
  --date 2020-09-15 \    # Date to simulate
  --speed 100 \          # Simulation speed (100x)
  --port 5000            # Dashboard port
```

---

## 📊 Dashboard Features

### 1. Real-Time Monitoring
- **Account Summary**: Capital, P&L, Total Value
- **Activity Metrics**: Ticks processed, Signals, Orders
- **System Status**: Running/Stopped, Current time, Last update

### 2. Strategy Overview
- View all active strategies
- See which symbols each strategy is trading
- Monitor strategy status (Active/Inactive)

### 3. Position Tracking
- Real-time position updates
- Entry price vs Current price
- Live P&L calculation
- Position quantity

### 4. Activity Logs
- Last 50 log entries
- Color-coded by level (INFO, WARNING, ERROR)
- Timestamps for all events
- Auto-scrolling display

---

## 🎨 Dashboard Layout

```
┌─────────────────────────────────────────────────────┐
│  🚀 VELOX Trading System          [RUNNING] ●       │
└─────────────────────────────────────────────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ 💰 Account   │  │ 📊 Activity  │  │ ⏰ System    │
│              │  │              │  │              │
│ Capital      │  │ Ticks: 3730  │  │ Status: Run  │
│ P&L          │  │ Signals: 5   │  │ Time: 15:15  │
│ Total Value  │  │ Orders: 3    │  │ Updated: Now │
└──────────────┘  └──────────────┘  └──────────────┘

┌──────────────────────┐  ┌──────────────────────┐
│ 🎯 Active Strategies │  │ 📈 Open Positions    │
│                      │  │                      │
│ Strategy ID | Status │  │ Symbol | Qty | P&L  │
│ rsi_agg    | Active │  │ ABB    | 10  | +50  │
└──────────────────────┘  └──────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 📝 Recent Activity Logs                             │
│                                                     │
│ [15:15:00] [WARNING] Square-off time reached       │
│ [15:00:00] [WARNING] 15 minutes to square-off      │
│ [14:30:15] [INFO] Signal: BUY ABB @ 915.50         │
│ [14:30:15] [INFO] Order filled: BUY ABB            │
└─────────────────────────────────────────────────────┘
```

---

## 🔄 Auto-Refresh

The dashboard automatically refreshes every **1 second** with:
- Latest account information
- Current positions
- Recent logs
- System status

---

## 🎯 What You'll See

### During Simulation:

1. **Initialization Phase:**
   ```
   Status: STOPPED → RUNNING
   Logs: "System initializing..."
         "Data manager loaded: 6 symbols"
         "Broker connected"
         "Strategy loaded: test_strategy (ABB)"
   ```

2. **Active Trading:**
   ```
   Ticks: Counting up (0 → 3730)
   Time: Advancing (09:15 → 15:30)
   Logs: "Processed 500 ticks, time: 10:30:00"
         "Signal: BUY ABB @ 915.50"
         "Order filled: BUY ABB"
   ```

3. **Time Warnings:**
   ```
   [15:00:00] ⚠️ 15 minutes to square-off
   [15:15:00] 🔔 Square-off time reached
   ```

4. **Completion:**
   ```
   Status: RUNNING → STOPPED
   Logs: "Simulation completed"
         "Final stats: 3730 ticks, 5 signals, 3 orders"
   ```

---

## 💡 Tips

### 1. Best Speed Settings:
- **Speed 10-50**: See updates in real-time
- **Speed 100**: Good balance of speed and visibility
- **Speed 1000**: Fast completion, fewer updates

### 2. Monitoring Signals:
Watch the logs section for:
- `Signal: BUY/SELL` - Strategy generated signal
- `Order filled` - Order executed successfully
- `WARNING` - Risk blocks or time warnings

### 3. P&L Tracking:
- Green numbers = Profit
- Red numbers = Loss
- Updates in real-time as prices change

### 4. Multiple Browser Tabs:
You can open multiple browser tabs to view the same dashboard.

---

## 🛠️ Troubleshooting

### Dashboard Not Loading:
```bash
# Check if port is already in use
lsof -i :5000

# Try different port
python run_with_dashboard.py --port 5001
```

### No Data Showing:
- Wait a few seconds for simulation to start
- Check terminal for error messages
- Verify date has data available

### Slow Updates:
- Reduce simulation speed (--speed 50)
- Check system resources
- Close other applications

---

## 📱 Mobile Friendly

The dashboard is responsive and works on:
- Desktop browsers (Chrome, Firefox, Safari, Edge)
- Tablets
- Mobile phones

---

## 🎨 Color Coding

### Status Badges:
- 🟢 **Green (RUNNING)**: System active
- 🔴 **Red (STOPPED)**: System inactive

### P&L Colors:
- 🟢 **Green**: Positive P&L
- 🔴 **Red**: Negative P&L

### Log Levels:
- 🔵 **Blue (INFO)**: Normal operations
- 🟡 **Yellow (WARNING)**: Important notices
- 🔴 **Red (ERROR)**: Errors occurred

---

## 🚀 Advanced Usage

### Run Multiple Simulations:
```bash
# Terminal 1: First simulation
python run_with_dashboard.py --date 2020-09-15 --port 5000

# Terminal 2: Second simulation
python run_with_dashboard.py --date 2020-09-16 --port 5001
```

### Custom Configuration:
Edit `config/strategies.yaml` before running to change:
- Strategy parameters
- Symbols to trade
- Risk limits

---

## 📊 API Endpoints

The dashboard exposes REST APIs:

```bash
# Get system status
curl http://localhost:5000/api/status

# Get strategies
curl http://localhost:5000/api/strategies

# Get positions
curl http://localhost:5000/api/positions

# Get account info
curl http://localhost:5000/api/account
```

---

## 🎉 Enjoy!

The dashboard provides real-time visibility into your trading system's operations. Watch your strategies in action!

**Happy Trading! 🚀**
