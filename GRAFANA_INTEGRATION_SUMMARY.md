# Grafana Trade Verification Dashboard - Integration Summary

## Overview

A comprehensive Grafana dashboard has been integrated into the VELOX trading system to provide real-time trade verification, monitoring, and analysis. The dashboard dynamically adapts to all running strategies and includes detailed metrics for verifying trade correctness.

## What Was Added

### 1. Enhanced InfluxDB Data Collection

**File**: `src/database/influx_manager.py`

Added three new measurements for detailed trade verification:

#### a) `signals` Measurement
Captures ALL trading signals (both approved and rejected):
- Strategy ID, symbol, action (BUY/SELL)
- Signal status (approved/rejected)
- Price, quantity, reason
- Rejection reason (if rejected)
- **All technical indicator values at signal generation time**

#### b) `order_execution` Measurement
Tracks order execution quality:
- Requested vs filled prices
- Absolute and percentage slippage
- Fill time in milliseconds
- Strategy, symbol, order ID

#### c) `trade_details` Measurement
Comprehensive trade information:
- Entry and exit prices
- Quantity, P&L, P&L percentage
- Trade duration in seconds
- Exit reason
- **Indicator values at both entry and exit**

### 2. Data Manager Integration

**File**: `src/database/data_manager.py`

Added three new logging methods:
- `log_signal()` - Log all signals with indicator values
- `log_order_execution()` - Log execution quality metrics
- `log_trade_complete()` - Log complete trade details

### 3. Main System Integration

**File**: `src/main.py`

Integrated logging calls in the trading loop:
- Log every signal (approved and rejected) with indicator values
- Log order execution quality after each fill
- Capture indicator snapshots from strategies

### 4. Grafana Dashboard

**File**: `grafana/dashboards/velox-trade-verification.json`

Comprehensive 24-panel dashboard with 9 sections:

#### 📊 Overview - Key Metrics (6 panels)
- Total P&L (24h)
- Total Trades count
- Win Rate gauge
- Open Positions count
- Signal Approval Rate
- Cumulative P&L chart

#### 🔍 Trade Execution Verification (1 panel)
- Complete trade history table with:
  - Entry/Exit prices, quantity, P&L
  - Trade duration, exit reason
  - Color-coded P&L (green=profit, red=loss)

#### 📡 Signal Analysis (2 panels)
- Approved vs Rejected pie chart
- All signals table with:
  - Signal status, reason, rejection reason
  - **All indicator values at signal time**

#### 📈 Real-time Position Monitoring (2 panels)
- Position P&L over time (by symbol)
- Trailing stop-loss levels tracking

#### ⚡ Order Execution Quality (2 panels)
- Slippage % per order chart
- Order execution details table:
  - Requested vs filled prices
  - Slippage analysis
  - Fill time metrics

#### 📊 Technical Indicators (3 panels)
- RSI indicator (all symbols)
- EMA/SMA indicators
- ATR indicator

#### 🛡️ Risk Metrics & Limits (4 panels)
- Total open positions gauge (max: 5)
- Daily P&L gauge (limit: -$5000)
- Positions per strategy pie chart (max: 3 each)
- Daily loss tracking chart

#### ⏱️ Trade Timeline (1 panel)
- Chronological BUY/SELL events
- Green points for BUY, red points for SELL

#### 📈 Performance Statistics (3 panels)
- P&L by strategy (hourly bars)
- Win rate by strategy over time
- Performance summary table (by strategy & symbol)

### 5. Grafana Provisioning

**Files**:
- `grafana/provisioning/datasources/influxdb.yml` - Auto-configures InfluxDB datasource
- `grafana/provisioning/dashboards/dashboard.yml` - Auto-loads dashboard

### 6. Documentation

**File**: `grafana/README.md`

Comprehensive 400+ line guide covering:
- Dashboard features and panels
- Setup instructions
- Trade verification workflow
- Troubleshooting guide
- Performance optimization
- Best practices

### 7. Setup Script

**File**: `setup_grafana_dashboard.sh`

Automated setup script that:
- Checks prerequisites
- Starts all Docker services
- Verifies service health
- Provides access instructions

## Dynamic Features

### 1. Strategy Filters
Dashboard includes template variables that automatically detect:
- All active strategies
- All traded symbols
- Filters update every refresh cycle

### 2. Auto-Refresh
- Default: 5 second refresh
- Configurable: 5s, 10s, 30s, 1m, 5m, 15m, 30m, 1h, 2h, 1d

### 3. Time Range Selection
- Default: Last 24 hours
- Customizable to any time range
- Zoom and pan on all charts

### 4. Real-time Updates
- All panels update automatically
- Live data as trades execute
- No manual refresh needed

## How Trade Verification Works

### 1. Signal Verification
1. Navigate to **📡 Signal Analysis**
2. Review "All Signals" table
3. Check indicator values (columns starting with `ind_`)
4. Verify signal reasons match strategy logic
5. Review rejection reasons for rejected signals

### 2. Execution Verification
1. Navigate to **⚡ Order Execution Quality**
2. Compare requested vs filled prices
3. Check slippage percentages
4. Verify no excessive slippage (should be < 0.5%)

### 3. Trade Result Verification
1. Navigate to **🔍 Trade Execution Verification**
2. Review entry/exit prices
3. Verify P&L calculations
4. Check exit reasons (should match strategy)
5. Validate trade duration

### 4. Risk Compliance Verification
1. Navigate to **🛡️ Risk Metrics & Limits**
2. Ensure open positions ≤ 5
3. Verify daily loss > -$5000
4. Check no strategy has > 3 positions
5. Monitor cumulative losses

## Quick Start

### 1. Setup
```bash
# Run automated setup
./setup_grafana_dashboard.sh

# Or manually
docker-compose up -d redis influxdb kafka grafana
```

### 2. Access Dashboard
- URL: http://localhost:3000
- Username: `admin`
- Password: `velox123`
- Dashboard: "VELOX Trade Verification Dashboard"

### 3. Generate Data
```bash
# Run a simulation
python3 velox.py --date 2024-01-15 --speed 100
```

### 4. View Dashboard
- Dashboard will populate with real-time data
- All panels update automatically
- Use filters to focus on specific strategies/symbols

## Key Benefits

### 1. Trade Verification
✅ See exact indicator values at signal generation time
✅ Verify signal reasons match strategy logic
✅ Check if rejections are appropriate
✅ Validate entry/exit decisions

### 2. Execution Quality
✅ Monitor slippage on every order
✅ Identify execution issues
✅ Track fill times
✅ Compare requested vs actual prices

### 3. Risk Monitoring
✅ Real-time position limit tracking
✅ Daily loss limit monitoring
✅ Per-strategy position limits
✅ Automatic alerts when limits approached

### 4. Performance Analysis
✅ Compare strategies head-to-head
✅ Track win rates over time
✅ Identify best/worst performers
✅ Symbol-specific performance breakdown

### 5. Debugging
✅ See why trades were taken
✅ Understand exit reasons
✅ Review indicator values at critical moments
✅ Identify strategy logic issues

## Technical Details

### Data Flow

```
Trading Signal Generated
    ↓
Indicators Captured
    ↓
Risk Manager Validates
    ↓
Signal Logged (approved/rejected) → InfluxDB
    ↓ (if approved)
Order Executed
    ↓
Execution Logged (slippage, fill time) → InfluxDB
    ↓
Position Updated
    ↓
Trade Complete Logged (full details) → InfluxDB
    ↓
Grafana Queries InfluxDB
    ↓
Dashboard Updates (5s refresh)
```

### InfluxDB Schema

**Bucket**: `trading`
**Organization**: `velox`
**Retention**: Configurable (default: infinite)

**New Measurements**:
1. `signals` - All trading signals
2. `order_execution` - Execution quality metrics
3. `trade_details` - Complete trade information

### Grafana Configuration

**Datasource**: InfluxDB v2 (Flux)
**Connection**: http://influxdb:8086
**Auth**: Token-based
**Provisioning**: Automatic on startup

## Files Modified

### Core System
- `src/database/influx_manager.py` - Added 3 new write methods
- `src/database/data_manager.py` - Added 3 new logging methods
- `src/main.py` - Integrated logging calls

### Grafana
- `grafana/provisioning/datasources/influxdb.yml` - Datasource config
- `grafana/provisioning/dashboards/dashboard.yml` - Dashboard provisioning
- `grafana/dashboards/velox-trade-verification.json` - Dashboard definition

### Documentation
- `grafana/README.md` - Comprehensive user guide
- `GRAFANA_INTEGRATION_SUMMARY.md` - This file
- `setup_grafana_dashboard.sh` - Setup script

### Configuration
- `docker-compose.yml` - Already configured (no changes needed)

## Maintenance

### Monitoring Dashboard Health
```bash
# Check Grafana logs
docker-compose logs -f grafana

# Check InfluxDB data
docker exec -it velox-influxdb influx query \
  --org velox \
  --token velox-super-secret-token \
  'from(bucket: "trading") |> range(start: -1h) |> limit(n: 10)'
```

### Performance Tuning

For large datasets:
1. Increase aggregation windows (1m instead of 10s)
2. Reduce refresh rate (30s instead of 5s)
3. Use filters (strategy/symbol) when analyzing
4. Set appropriate time ranges (don't query all data)

### Data Retention

Set retention policy for InfluxDB:
```bash
docker exec -it velox-influxdb influx bucket update \
  --name trading \
  --org velox \
  --retention 30d \
  --token velox-super-secret-token
```

## Troubleshooting

### Dashboard Shows "No Data"

**Solution 1**: Run a simulation first
```bash
python3 velox.py --date 2024-01-15 --speed 100
```

**Solution 2**: Check InfluxDB connection
1. Go to Grafana → Configuration → Data Sources
2. Click "InfluxDB-VELOX"
3. Click "Save & Test" (should show "datasource is working")

**Solution 3**: Verify data exists
```bash
docker exec -it velox-influxdb influx query \
  --org velox \
  --token velox-super-secret-token \
  'from(bucket: "trading") |> range(start: -24h) |> group() |> count()'
```

### Dashboard Not Auto-Loading

**Solution**: Restart Grafana
```bash
docker-compose restart grafana
# Wait 15 seconds for startup
```

### Panels Show Errors

**Solution**: Check query syntax
1. Edit panel
2. Review Flux query
3. Click "Run queries"
4. Check for errors in query result

## Future Enhancements

Potential improvements:
1. Add email/Slack alerts for:
   - High slippage (> 0.5%)
   - Daily loss approaching limit
   - Win rate drops below threshold
2. Add ML-based anomaly detection
3. Add strategy comparison overlay
4. Add trade entry/exit annotations
5. Add backtesting comparison view
6. Add live vs. backtest performance comparison

## Support

### Documentation
- Dashboard Guide: `grafana/README.md`
- System Docs: `docs/` directory
- Grafana Docs: https://grafana.com/docs/

### Troubleshooting
- Check logs: `docker-compose logs <service>`
- Verify services: `docker-compose ps`
- Test connections: See grafana/README.md

---

**Version**: 1.0
**Date**: 2025-10-22
**Author**: Claude
**Status**: Production Ready
