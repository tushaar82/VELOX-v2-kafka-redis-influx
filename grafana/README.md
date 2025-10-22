# VELOX Grafana Trade Verification Dashboard

## Overview

This comprehensive Grafana dashboard is designed to help you verify trades executed by the VELOX trading system. It provides real-time monitoring, detailed analytics, and dynamic adaptation to all running strategies.

## Dashboard Features

### 📊 Overview - Key Metrics
- **Total P&L (24h)**: Cumulative profit/loss for the last 24 hours
- **Total Trades**: Number of trades executed
- **Win Rate**: Percentage of profitable trades
- **Open Positions**: Current number of open positions
- **Signal Approval Rate**: Percentage of signals approved by risk manager
- **Cumulative P&L Chart**: Visual representation of P&L over time

### 🔍 Trade Execution Verification
- **Complete Trade History Table**: Shows all trades with:
  - Entry/Exit prices
  - Quantity, P&L, P&L percentage
  - Trade duration in seconds
  - Exit reason (stop-loss, take-profit, strategy signal, etc.)
  - Strategy and symbol information
  - Color-coded P&L (green for profit, red for loss)

### 📡 Signal Analysis
- **Approved vs Rejected Pie Chart**: Visual breakdown of signal approval status
- **All Signals Table**: Comprehensive signal log with:
  - Signal timestamp
  - Strategy, symbol, action (BUY/SELL)
  - Signal status (approved/rejected)
  - Price and quantity
  - Signal reason
  - Rejection reason (if rejected)
  - All technical indicator values at signal generation time

### 📈 Real-time Position Monitoring
- **Position P&L Over Time**: Track unrealized P&L for each open position by symbol
- **Trailing Stop-Loss Levels**: Monitor stop-loss levels and highest prices reached

### ⚡ Order Execution Quality
- **Slippage % per Order**: Bar chart showing slippage for each order
- **Order Execution Details Table**:
  - Requested vs Filled prices
  - Absolute and percentage slippage
  - Fill time in milliseconds
  - Strategy, symbol, and action

### 📊 Technical Indicators at Trade Time
- **RSI Indicator**: Real-time RSI values for all symbols
- **EMA/SMA Indicators**: Moving average values
- **ATR Indicator**: Average True Range for volatility measurement

### 🛡️ Risk Metrics & Limits
- **Total Open Positions Gauge**: Current positions vs maximum allowed (5)
- **Daily P&L Gauge**: Current daily P&L vs loss limit (-$5000)
- **Positions per Strategy**: Pie chart showing position distribution (max 3 per strategy)
- **Daily Loss Tracking**: Real-time tracking against daily loss limit

### ⏱️ Trade Timeline & Events
- **Trade Timeline**: Chronological view of all BUY/SELL events
  - Green points for BUY orders
  - Red points for SELL orders

### 📈 Performance Statistics by Strategy
- **P&L by Strategy (Hourly)**: Bar chart comparing strategy performance
- **Win Rate by Strategy Over Time**: Track win rate evolution for each strategy
- **Performance Summary Table**: Aggregated P&L by strategy and symbol

## Dynamic Features

### Strategy Filters
The dashboard includes template variables that automatically detect all strategies from your data:
- **Strategy Filter**: Select one or more strategies to focus on
- **Symbol Filter**: Filter by specific trading symbols
- Filters auto-update every refresh cycle

### Auto-Refresh
- Default refresh: Every 5 seconds
- Configurable refresh intervals: 5s, 10s, 30s, 1m, 5m, 15m, 30m, 1h, 2h, 1d

## Setup Instructions

### 1. Start Infrastructure
```bash
# Start all required services
docker-compose up -d redis influxdb kafka zookeeper grafana

# Verify services are running
docker-compose ps
```

### 2. Access Grafana
- URL: http://localhost:3000
- Username: `admin`
- Password: `velox123`

### 3. Dashboard Auto-Loading
The dashboard is automatically provisioned when Grafana starts. You should see:
- **InfluxDB-VELOX** datasource configured automatically
- **VELOX Trade Verification Dashboard** available in the dashboards list

### 4. Manual Dashboard Import (if needed)
If the dashboard doesn't auto-load:
1. Click **Dashboards** → **Import**
2. Upload `grafana/dashboards/velox-trade-verification.json`
3. Select **InfluxDB-VELOX** as the datasource
4. Click **Import**

## Using the Dashboard

### Verifying Trade Correctness

#### 1. Check Signal Generation
Navigate to **📡 Signal Analysis** section:
- Review all signals in the table
- Check indicator values at signal time (columns starting with `ind_`)
- Verify signal reasons make sense
- Check rejection reasons for rejected signals

#### 2. Verify Order Execution
Navigate to **⚡ Order Execution Quality** section:
- Compare requested vs filled prices
- Check slippage is within acceptable range (typically < 0.1%)
- Verify no excessive fill times

#### 3. Validate Trade Results
Navigate to **🔍 Trade Execution Verification** section:
- Review entry and exit prices
- Check P&L calculations
- Verify exit reasons (should match strategy logic)
- Compare trade duration against strategy parameters

#### 4. Monitor Risk Compliance
Navigate to **🛡️ Risk Metrics & Limits** section:
- Ensure open positions stay within limits
- Monitor daily loss doesn't breach -$5000
- Verify no strategy exceeds 3 positions
- Track cumulative losses

### Finding Issues

#### High Slippage
If you see excessive slippage (> 0.5%):
- Check **Order Execution Details** table
- Identify which symbols/strategies affected
- Review market conditions at those times
- Consider adjusting slippage parameters in system.yaml

#### Rejected Signals
If signal approval rate is low (< 70%):
- Check **All Signals** table
- Review rejection reasons
- Common reasons:
  - Max positions reached
  - Daily loss limit exceeded
  - Position size too large
- Adjust risk parameters if needed

#### Unexpected Exits
If trades exit unexpectedly:
- Check **Trade Details** table
- Review exit reasons
- Verify stop-loss levels in **Real-time Position Monitoring**
- Check if trailing stop-loss is behaving correctly

#### Strategy Underperformance
If a strategy shows poor results:
- Compare **P&L by Strategy** chart
- Review **Win Rate by Strategy Over Time**
- Check **Performance Summary Table** for symbol-specific issues
- Analyze **Technical Indicators** during losing trades

### Advanced Analysis

#### Custom Time Ranges
Use the time picker (top right) to analyze specific periods:
- Click on time range
- Select preset (Last 5 minutes, Last 30 minutes, etc.)
- Or set custom absolute time range

#### Zooming and Panning
- Click and drag on any chart to zoom in
- Double-click to reset zoom
- Use mouse wheel to zoom in/out

#### Data Export
1. Click on any table panel
2. Click **...** (three dots) in panel header
3. Select **Inspect** → **Data**
4. Click **Download CSV** or **Download logs**

## Troubleshooting

### Dashboard Shows No Data

#### Check InfluxDB Connection
```bash
# Verify InfluxDB is running
docker-compose logs influxdb

# Check if bucket exists
docker exec -it velox-influxdb influx bucket list --org velox --token velox-super-secret-token
```

#### Verify Data is Being Written
```bash
# Check recent data points
docker exec -it velox-influxdb influx query \
  --org velox \
  --token velox-super-secret-token \
  'from(bucket: "trading") |> range(start: -1h) |> limit(n: 10)'
```

#### Check Grafana Datasource
1. Go to **Configuration** → **Data Sources**
2. Click **InfluxDB-VELOX**
3. Scroll down and click **Save & Test**
4. Should show "datasource is working"

### Panels Show "No Data"

#### Check Query
1. Click on panel title → **Edit**
2. Review the Flux query
3. Click **Run queries** to test
4. Adjust time range if needed

#### Verify Measurement Exists
Common measurements:
- `trades` - Trade executions
- `signals` - All signals (approved/rejected)
- `positions` - Open position snapshots
- `order_execution` - Order execution details
- `trade_details` - Comprehensive trade info
- `indicators` - Technical indicator values
- `trailing_sl` - Stop-loss updates

### Dashboard Not Auto-Loading

#### Check Provisioning
```bash
# Verify provisioning files exist
ls -la grafana/provisioning/datasources/
ls -la grafana/provisioning/dashboards/
ls -la grafana/dashboards/

# Check Grafana logs
docker-compose logs grafana | grep -i provision
```

#### Restart Grafana
```bash
docker-compose restart grafana
```

## Data Retention

### InfluxDB Default Retention
- Default: Infinite retention
- To set retention policy:
```bash
docker exec -it velox-influxdb influx bucket update \
  --name trading \
  --org velox \
  --retention 30d \
  --token velox-super-secret-token
```

### Redis Cache
- Position data: 24 hours TTL
- Indicator snapshots: 24 hours TTL
- Latest ticks: 24 hours TTL

## Performance Optimization

### For Large Datasets

#### Adjust Aggregation Windows
Edit panel queries to use larger windows:
```flux
|> aggregateWindow(every: 1m, fn: last, createEmpty: false)  // Instead of every: 10s
```

#### Limit Data Points
```flux
|> limit(n: 100)  // Limit results
```

#### Use Filters
Always filter by strategy or symbol when analyzing specific data:
- Use template variables at top of dashboard
- Add filters in query: `|> filter(fn: (r) => r["strategy_id"] == "supertrend_simple")`

### Dashboard Loading Issues

#### Reduce Refresh Rate
- Change from 5s to 10s or 30s
- Top right corner → **Refresh** dropdown

#### Disable Auto-Refresh
- Set refresh to "Off" when doing detailed analysis

## Customization

### Adding Custom Panels

1. Click **Add panel** at top right
2. Select **Add a new panel**
3. Configure query:
```flux
from(bucket: "trading")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] == "your_measurement")
  |> filter(fn: (r) => r["_field"] == "your_field")
```
4. Choose visualization type
5. Click **Apply**

### Modifying Existing Panels

1. Click panel title → **Edit**
2. Modify query, visualization, or settings
3. Click **Apply** to save
4. Click **Save dashboard** (top right)

### Changing Thresholds

Edit gauges and stats to adjust warning/critical thresholds:
1. Panel edit mode
2. Right sidebar → **Thresholds**
3. Adjust values and colors
4. Apply changes

## Best Practices

### Daily Trade Verification Routine

1. **Morning Check** (before market open):
   - Review previous day's P&L
   - Check win rate trends
   - Verify no risk limit breaches

2. **During Trading** (real-time):
   - Monitor **Open Positions** panel
   - Watch **Order Execution Quality** for slippage spikes
   - Check **Signal Approval Rate** stays healthy

3. **End of Day** (after market close):
   - Review **Trade Details** table
   - Analyze losing trades
   - Check **Performance by Strategy**
   - Export data for further analysis

### Alert Configuration

Set up alerts for critical conditions:
1. Edit panel → **Alert** tab
2. Configure condition (e.g., Daily P&L < -$4000)
3. Set notification channel (email, Slack, etc.)
4. Save alert

Example alert conditions:
- Daily loss approaching limit (-$4500)
- Win rate drops below 40%
- Open positions reach maximum (5)
- High slippage detected (> 0.5%)

## Support

### Getting Help
- Check Grafana docs: https://grafana.com/docs/
- InfluxDB Flux language: https://docs.influxdata.com/flux/
- VELOX system logs: `logs/velox_*.log`

### Reporting Issues
If you encounter dashboard issues:
1. Check Docker container logs
2. Verify InfluxDB data exists
3. Test datasource connection
4. Review Grafana server logs

---

**Dashboard Version**: 1.0
**Last Updated**: 2025-10-22
**Compatible with**: VELOX v2 (Kafka-Redis-InfluxDB)
