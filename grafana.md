GRAFANA DASHBOARD INTEGRATION PLAN FOR VELOX TRADING SYSTEM
📊 DASHBOARD OBJECTIVES
Trade Verification: Verify correctness of trades by showing entry/exit logic, indicator values at signal time
Tiny Details: Display every micro-detail (indicator values, reasons, conditions, timings)
Dynamic Adaptation: Auto-detect and display all running strategies with their specific metrics
Real-time Monitoring: Live updates from InfluxDB and Redis
Historical Analysis: Review past trades with full context


##PHASE 1: INFRASTRUCTURE SETUP##
Step 1.1: Add Grafana to Docker Compose
Instructions for AI Agent:

Open file: docker-compose.yml
Add a new service named grafana after the existing services
Configuration details:
Use image: grafana/grafana:latest
Container name: velox-grafana
Expose port: 3000:3000
Environment variables:
GF_SECURITY_ADMIN_PASSWORD=velox123
GF_SECURITY_ADMIN_USER=admin
GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource,grafana-piechart-panel
GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/etc/grafana/provisioning/dashboards/velox-main.json
Create volumes:
grafana-data:/var/lib/grafana
./grafana/provisioning:/etc/grafana/provisioning
./grafana/dashboards:/etc/grafana/provisioning/dashboards
Add healthcheck with curl to http://localhost:3000/api/health
Set restart policy: unless-stopped
Make it depend on: influxdb and redis
Add volume definition at bottom: grafana-data:
Step 1.2: Create Grafana Directory Structure
Instructions for AI Agent:

Create directory structure:
grafana/
├── provisioning/
│   ├── datasources/
│   │   └── influxdb.yml
│   └── dashboards/
│       └── dashboard.yml
└── dashboards/
    ├── velox-main.json
    ├── velox-trade-verification.json
    ├── velox-strategy-performance.json
    └── velox-risk-monitoring.json
Step 1.3: Configure InfluxDB Data Source
Instructions for AI Agent:

Create file: grafana/provisioning/datasources/influxdb.yml
Configure:
API version: 1
Datasource type: influxdb
Name: InfluxDB-VELOX
URL: http://influxdb:8086
Access mode: proxy
Database: trading
User: admin
Secure JSON data:
Token: velox-super-secret-token
Organization: velox
Default bucket: trading
Query language: Flux
Set as default: true
Set editable: false
Step 1.4: Configure Dashboard Auto-Provisioning
Instructions for AI Agent:

Create file: grafana/provisioning/dashboards/dashboard.yml
Configure:
API version: 1
Provider name: VELOX Dashboards
Provider type: file
Disable deletion: false
Update interval seconds: 10
Options:
Path: /etc/grafana/provisioning/dashboards
Folder: VELOX Trading
PHASE 2: DATA PIPELINE ENHANCEMENT
Step 2.1: Enhance InfluxDB Data Structure
Instructions for AI Agent:

Open file: src/database/influx_manager.py
Add new measurement schemas for Grafana:
Measurement 1: trade_details (Enhanced trade tracking)

Fields to add:
All existing trade fields PLUS:
entry_indicator_rsi (float)
entry_indicator_ma_20 (float)
entry_indicator_ma_50 (float)
entry_indicator_atr (float)
entry_indicator_supertrend (float)
entry_volume (float)
entry_volume_avg_ratio (float)
exit_indicator_rsi (float)
exit_indicator_ma_20 (float)
hold_duration_minutes (float)
slippage_pct (float)
max_favorable_excursion (float) - highest profit during trade
max_adverse_excursion (float) - worst drawdown during trade
signal_conditions_json (string) - JSON of all conditions
exit_reason_detailed (string)
Tags: strategy_id, symbol, action, is_winner (boolean tag), exit_type
Measurement 2: signal_analysis (All signals including rejected)

Fields:
signal_price (float)
signal_quantity (int)
signal_reason (string)
risk_approved (boolean)
risk_rejection_reason (string)
position_size_requested (float)
position_size_approved (float)
All indicator values at signal time
Tags: strategy_id, symbol, action, signal_status (approved/rejected)
Measurement 3: strategy_health (Real-time strategy metrics)

Fields:
open_positions_count (int)
total_trades_today (int)
win_count (int)
loss_count (int)
win_rate_pct (float)
avg_win_pct (float)
avg_loss_pct (float)
profit_factor (float) - total wins / total losses
sharpe_ratio (float)
max_drawdown_pct (float)
total_pnl (float)
avg_trade_duration_minutes (float)
signals_generated_today (int)
signals_approved_today (int)
approval_rate_pct (float)
is_active (boolean)
Tags: strategy_id, strategy_type
Write frequency: Every 30 seconds
Measurement 4: tick_analysis (Enhanced tick data)

Add to existing ticks measurement:
tick_momentum (float) - price change velocity
spread_bps (float) - bid-ask spread in basis points
volume_intensity (float) - volume compared to average
Step 2.2: Create Data Writer Service
Instructions for AI Agent:

Create new file: src/database/grafana_data_writer.py
This service should:
Run in a separate thread
Subscribe to Kafka topics: velox-signals, velox-trades, velox-positions
On each event, write enhanced data to InfluxDB
Calculate and write strategy health metrics every 30 seconds
Maintain a buffer for batch writes (50 points at a time)
Include retry logic with exponential backoff
Log all write operations with timestamp
Step 2.3: Enhance Trade Execution Logging
Instructions for AI Agent:

Modify file: src/core/order_manager.py
In the execute_signal() method:
Before executing: Capture ALL current indicator values
After execution: Write to trade_details measurement with full context
Store entry conditions as JSON string
Modify file: src/core/position_manager.py
In the close_position() method:
Calculate max_favorable_excursion (track highest price during position)
Calculate max_adverse_excursion (track lowest price during position)
Capture ALL indicator values at exit
Write complete trade record to trade_details
Step 2.4: Enhance Signal Logging
Instructions for AI Agent:

Modify file: src/core/risk_manager.py
In the validate_signal() method:
Write every signal (approved AND rejected) to signal_analysis measurement
Include detailed rejection reasons
Log position size calculations
Store complete risk check results
PHASE 3: DASHBOARD CREATION
DASHBOARD 1: Main Trading Overview
File: grafana/dashboards/velox-main.json

Instructions for AI Agent:

Create a Grafana dashboard JSON with the following panels:
Row 1: Real-Time System Status (Height: 150px)

Panel 1.1: Active Strategies Count (Stat panel)

Query: Count distinct strategy_ids from strategy_health where is_active=true in last 1 minute
Display: Large number with sparkline
Color: Green if > 0, Red if 0
Panel 1.2: Total Open Positions (Stat panel)

Query: Sum of open_positions_count from strategy_health in last 1 minute
Display: Large number
Threshold: Green (0-3), Yellow (4-5), Red (>5)
Panel 1.3: Total P&L Today (Stat panel)

Query: Sum of total_pnl from strategy_health in last 1 minute
Display: Currency format with + or - prefix
Color: Green if positive, Red if negative
Show change from 5 minutes ago
Panel 1.4: Win Rate Today (Gauge panel)

Query: Weighted average of win_rate_pct from strategy_health
Display: Gauge from 0-100%
Thresholds: Red (0-40), Yellow (40-60), Green (60-100)
Panel 1.5: Signals Generated Today (Stat panel)

Query: Sum of signals_generated_today from strategy_health
Display: Number with trend arrow
Panel 1.6: Signal Approval Rate (Stat panel)

Query: Average of approval_rate_pct from strategy_health
Display: Percentage
Thresholds: Red (0-30), Yellow (30-70), Green (70-100)
Row 2: Strategy Performance Matrix (Height: 300px)

Panel 2.1: Strategy P&L Comparison (Bar chart)

Query: total_pnl by strategy_id from strategy_health in last 5 minutes
X-axis: Strategy names
Y-axis: P&L in currency
Color: Green bars for positive, Red for negative
Add reference line at zero
Panel 2.2: Strategy Win Rates (Bar chart)

Query: win_rate_pct by strategy_id from strategy_health
X-axis: Strategy names
Y-axis: Win rate percentage
Color gradient: Red to Green
Show average line
Row 3: Live Positions Table (Height: 400px)

Panel 3.1: All Open Positions (Table panel)
Query: Get all positions from positions measurement where status != 'closed'
Columns to show:
Strategy ID
Symbol
Entry Time
Entry Price
Current Price
Quantity
Unrealized P&L ($)
Unrealized P&L (%)
Hold Duration (minutes)
Current Stop Loss
Distance to SL (%)
Entry RSI
Current RSI
Entry Reason
Sort: By Unrealized P&L % descending
Color coding: Green rows for profit, Red for loss
Auto-refresh: Every 5 seconds
Row 4: Trade Flow Timeline (Height: 300px)

Panel 4.1: Trades Over Time (Time series)

Query: Count of trades from trade_details grouped by 5-minute intervals
Show separate lines for BUY and SELL
Show wins vs losses with different colors
Stack: Stacked area chart
Panel 4.2: P&L Distribution (Histogram)

Query: pnl_pct from trade_details for last 24 hours
Bins: -5% to +5% in 0.5% increments
Color: Green for positive bins, Red for negative
Show mean and median lines
Row 5: Market Activity (Height: 300px)

Panel 5.1: Symbols Trading Volume (Time series)

Query: Volume from ticks grouped by symbol
Multiple lines, one per symbol
Auto-legend on right
Panel 5.2: Active Symbols Heat Map (Heat map)

Query: Count of signals by symbol and hour of day
X-axis: Hour (9 AM to 3:30 PM)
Y-axis: Symbols
Color: Intensity of activity
DASHBOARD 2: Trade Verification Dashboard
File: grafana/dashboards/velox-trade-verification.json

Instructions for AI Agent:

This dashboard is critical for verifying trade correctness
Row 1: Trade Selection (Height: 100px)

Panel 1.1: Select Trade (Variable dropdown)
Query: Get all trade_ids from trade_details ordered by entry_time descending
Display format: {trade_id} - {symbol} {action} @ {entry_price} ({pnl_pct}%)
Multi-select: No
Include "All" option: No
Row 2: Trade Overview (Height: 200px)

Panel 2.1: Trade Summary Card (Stat panel grid)
Create 8 stat panels showing selected trade:
Strategy ID
Symbol
Action (BUY/SELL) with icon
Entry Time
Exit Time
Hold Duration
P&L ($)
P&L (%)
Use variables: $trade_id
Row 3: Entry Analysis (Height: 400px)

Panel 3.1: Entry Conditions Met (Table)

Parse signal_conditions_json for selected trade
Show each condition as a row:
Condition Name
Expected Value
Actual Value
Status (✓ or ✗)
Color code: Green for met, Red for not met
Panel 3.2: Indicators at Entry (Stat panel grid)

Show all indicator values at entry time:
RSI value (with oversold/overbought zones)
MA 20 value and price vs MA
MA 50 value and price vs MA
ATR value
Supertrend value and trend direction
Volume vs average (ratio)
Color code based on bullish/bearish context
Row 4: Price Chart During Trade (Height: 500px)

Panel 4.1: Trade Price Action (Time series with annotations)
Query: Get tick data from entry time to exit time for selected symbol
Plot: Candlestick chart (1-minute candles)
Add annotation line at entry price (green)
Add annotation line at exit price (red)
Add annotation line at stop loss price (orange dashed)
Add annotation line at target price (blue dashed)
Add shaded region for max favorable excursion
Add shaded region for max adverse excursion
Overlay: RSI in bottom panel
Overlay: Volume bars
Show entry/exit times as vertical lines with labels
Row 5: Exit Analysis (Height: 400px)

Panel 5.1: Exit Reason Breakdown (Table)

Show detailed exit reason from exit_reason_detailed
Parse and display:
Exit trigger (target hit, SL hit, time-based, etc.)
Indicators at exit (RSI, MA, ATR)
Profit/Loss metrics
Hold time evaluation
Include "Was this exit optimal?" analysis
Panel 5.2: Indicators at Exit (Stat panel grid)

Same as entry indicators panel but with exit values
Show delta from entry values
Row 6: Trade Efficiency Metrics (Height: 300px)

Panel 6.1: Efficiency Gauges

Max Favorable Excursion (MFE) gauge: 0-100%
Max Adverse Excursion (MAE) gauge: 0-100%
Efficiency ratio: (Exit P&L / MFE) * 100
Risk/Reward ratio: MFE / MAE
Panel 6.2: Trade Quality Score (Stat)

Calculate composite score (0-100) based on:
Entry timing quality (indicator alignment)
Exit timing quality (captured % of MFE)
Risk management (MAE vs SL)
Hold duration appropriateness
Color: Red (0-50), Yellow (50-75), Green (75-100)
Row 7: Similar Trades Comparison (Height: 300px)

Panel 7.1: Similar Trades (Table)
Query: Find trades with same strategy_id and symbol
Filter: Trades within ±10% of entry price
Show: Entry price, Exit price, P&L%, Hold time, Entry RSI, Exit reason
Highlight: Selected trade row
Purpose: Compare to see if this trade was typical
DASHBOARD 3: Strategy Performance Deep Dive
File: grafana/dashboards/velox-strategy-performance.json

Row 1: Strategy Selection (Height: 100px)

Panel 1.1: Select Strategy (Variable dropdown)
Query: Get distinct strategy_ids from strategy_health
Include "All" option: Yes
Row 2: Strategy Health Scorecard (Height: 200px)

Create grid of 12 stat panels for selected strategy:
Total Trades
Win Count
Loss Count
Win Rate %
Average Win %
Average Loss %
Profit Factor
Sharpe Ratio
Max Drawdown %
Total P&L
Avg Trade Duration
Current Open Positions
Row 3: Strategy Performance Over Time (Height: 400px)

Panel 3.1: Cumulative P&L (Time series)

Query: Running sum of P&L from trade_details for selected strategy
Add benchmark line (buy-and-hold) if possible
Color: Green area for above zero, Red below
Panel 3.2: Win Rate Evolution (Time series)

Query: Rolling 20-trade win rate
Show confidence bands
Add horizontal line at 50%
Row 4: Trade Distribution Analysis (Height: 400px)

Panel 4.1: P&L Distribution by Symbol (Box plot)

Query: P&L% grouped by symbol for selected strategy
Show median, quartiles, outliers
Purpose: Identify which symbols work best
Panel 4.2: P&L by Entry Hour (Bar chart)

Query: Average P&L% grouped by hour of day
X-axis: Trading hours (9 AM - 3:30 PM)
Purpose: Find optimal entry times
Row 5: Signal Analysis (Height: 400px)

Panel 5.1: Signals vs Executions (Time series)

Query: Count of signals generated vs signals approved vs trades executed
Three lines with different colors
Purpose: Identify if risk manager is blocking too many signals
Panel 5.2: Rejection Reasons (Pie chart)

Query: Count of rejected signals grouped by rejection reason
Purpose: Understand why signals are rejected
Row 6: Indicator Performance (Height: 400px)

Panel 6.1: Entry RSI Distribution (Histogram)

Query: entry_indicator_rsi from winning vs losing trades
Overlay: Two distributions
Purpose: Find optimal RSI entry range
Panel 6.2: Entry Indicator Correlation (Heatmap)

Query: Correlation matrix of indicators at entry vs P&L
Purpose: Identify which indicators are predictive
Row 7: Risk Metrics (Height: 400px)

Panel 7.1: Consecutive Wins/Losses (Time series with annotations)

Query: Track streaks of wins and losses
Annotate longest winning streak and losing streak
Purpose: Understand strategy consistency
Panel 7.2: Trade Duration vs P&L (Scatter plot)

Query: Hold duration (X) vs P&L% (Y) for all trades
Color: By win/loss
Trend line: Linear regression
Purpose: Find optimal hold time
DASHBOARD 4: Risk Monitoring
File: grafana/dashboards/velox-risk-monitoring.json

Row 1: Real-Time Risk Gauges (Height: 200px)

Panel 1.1: Position Size Risk (Gauge)

Query: (Sum of all position sizes / Total capital) * 100
Thresholds: Green (0-50%), Yellow (50-80%), Red (80-100%)
Alert: Trigger if > 80%
Panel 1.2: Concentration Risk (Gauge)

Query: (Largest position size / Total capital) * 100
Thresholds: Green (0-10%), Yellow (10-20%), Red (20-100%)
Panel 1.3: Daily Loss Limit (Gauge)

Query: (Today's realized loss / Daily loss limit) * 100
Thresholds: Green (0-60%), Yellow (60-90%), Red (90-100%)
Alert: Trigger if > 90%
Panel 1.4: Max Positions Risk (Gauge)

Query: (Current open positions / Max allowed) * 100
Thresholds: Green (0-60%), Yellow (60-90%), Red (90-100%)
Row 2: Position Analysis (Height: 400px)

Panel 2.1: Positions by Strategy (Pie chart)

Query: Count of open positions grouped by strategy_id
Show percentages
Panel 2.2: Position Size Distribution (Bar chart)

Query: Position sizes grouped by symbol
Sort: Largest to smallest
Color: By strategy
Row 3: Stop Loss Monitoring (Height: 400px)

Panel 3.1: Distance to Stop Loss (Table)

Query: All open positions with current price and stop loss
Columns: Symbol, Current Price, Stop Loss, Distance ($), Distance (%), Trailing SL Type
Sort: By distance ascending
Alert: Highlight positions within 0.5% of SL
Panel 3.2: Stop Loss Hits (Time series)

Query: Count of trades where exit_reason contains "stop loss" over time
Group by strategy
Purpose: Monitor if SL is too tight
Row 4: Correlation Risk (Height: 400px)

Panel 4.1: Symbol Correlation Matrix (Heatmap)

Query: Price correlation between all actively traded symbols
Purpose: Identify correlated positions (increased risk)
Panel 4.2: Strategy Correlation (Heatmap)

Query: P&L correlation between strategies
Purpose: Ensure strategies are diversified
Row 5: Drawdown Analysis (Height: 400px)

Panel 5.1: Equity Curve with Drawdown (Time series)

Query: Running total equity over time
Add underwater equity curve (drawdown visualization)
Shade drawdown regions in red
Panel 5.2: Max Drawdown by Strategy (Bar chart)

Query: Maximum drawdown percentage per strategy
Thresholds: Acceptable vs risky levels
PHASE 4: ALERTING & NOTIFICATIONS
Step 4.1: Create Alert Rules
Instructions for AI Agent:

In Grafana, create alert rules for critical events:
Alert 1: Position Size Limit Breach

Condition: Sum of position sizes > 80% of capital
Frequency: Check every 30 seconds
Notification: Send to email/Slack
Message: "WARNING: Position size at {value}% of capital (limit: 80%)"
Alert 2: Daily Loss Limit Approaching

Condition: Today's realized loss > 90% of daily limit
Frequency: Check every 1 minute
Notification: Critical alert
Message: "CRITICAL: Daily loss at {value}% of limit. Trading will halt at 100%."
Alert 3: Strategy Underperformance

Condition: Strategy win rate < 30% over last 20 trades
Frequency: Check every 5 minutes
Notification: Warning
Message: "Strategy {strategy_id} win rate dropped to {value}%. Review required."
Alert 4: Unusual Signal Rejection Rate

Condition: Signal approval rate < 50% in last hour
Frequency: Check every 10 minutes
Notification: Info alert
Message: "High signal rejection rate: {value}% approved. Check risk parameters."
Alert 5: Strategy Not Responding

Condition: No signals from active strategy in last 30 minutes
Frequency: Check every 5 minutes
Notification: Warning
Message: "Strategy {strategy_id} has not generated signals in 30+ minutes. Check health."
Step 4.2: Configure Alert Channels
Instructions for AI Agent:

Create file: grafana/provisioning/notifiers/alert-channels.yml
Configure:
Channel 1: Email (for critical alerts)
Channel 2: Slack webhook (for all alerts)
Channel 3: PagerDuty (for system failures)
PHASE 5: DYNAMIC STRATEGY DETECTION
Step 5.1: Create Strategy Registry Service
Instructions for AI Agent:

Create new file: src/core/strategy_registry.py
Purpose: Track all active strategies and their metadata
Functionality:
Auto-register strategies when they start
Store strategy metadata: ID, type, symbols, parameters, start time
Write to InfluxDB measurement: strategy_registry
Expose API endpoint for Grafana variables
Update every time a strategy is added/removed
Step 5.2: Create Grafana Variables for Auto-Discovery
Instructions for AI Agent:

In each dashboard JSON, add variables:
$strategies: Query from strategy_health WHERE is_active=true
$symbols: Query from positions or ticks (distinct symbols)
$timeframes: Query from strategy configurations
Set variables to:
Auto-refresh: Every 1 minute
Multi-value: Yes (where applicable)
Include All: Yes (where applicable)
Step 5.3: Create Dynamic Panel Generator
Instructions for AI Agent:

Create new file: src/dashboard/grafana_panel_generator.py
Purpose: Generate dashboard panels programmatically based on active strategies
Functionality:
Query active strategies from registry
For each strategy, create:
Performance panel
Open positions panel
Indicator-specific panels
Export as JSON
Update Grafana via API
Run frequency: Every 5 minutes
PHASE 6: TESTING & VALIDATION
Step 6.1: Create Dashboard Test Script
Instructions for AI Agent:

Create new file: tests/test_grafana_integration.py
Tests to implement:
Verify Grafana is accessible at http://localhost:3000
Verify InfluxDB datasource is connected
Verify all dashboards are loaded
Verify data is flowing to InfluxDB measurements
Query each measurement and check data freshness (< 30 seconds old)
Test each dashboard panel query for errors
Verify alerts are configured
Test alert triggers with simulated data
Step 6.2: Create Sample Data Generator
Instructions for AI Agent:

Create new file: scripts/generate_sample_grafana_data.py
Purpose: Generate realistic sample data for dashboard testing
Generate:
100+ sample trades across 3 strategies
Mix of wins and losses (60% win rate)
Various symbols
Realistic indicator values
Position snapshots every 30 seconds
Signal data (approved and rejected)
Write to InfluxDB
Use for visual testing of dashboards
Step 6.3: Performance Testing
Instructions for AI Agent:

Test dashboard performance under load:
Simulate 10,000 trades
5 active strategies
100+ positions
Measure dashboard load time (target: < 2 seconds)
Measure query execution time (target: < 500ms)
Test with multiple concurrent users (5+)
Monitor Grafana CPU/memory usage
PHASE 7: DOCUMENTATION & LAUNCH
Step 7.1: Create Dashboard User Guide
Instructions for AI Agent:

Create file: docs/GRAFANA_DASHBOARD_GUIDE.md
Include:
How to access dashboards
Explanation of each dashboard and its purpose
How to interpret each panel
How to verify trade correctness using the Trade Verification dashboard
Alert meanings and responses
Troubleshooting common issues
Screenshots of each dashboard
Step 7.2: Create Deployment Script
Instructions for AI Agent:

Create file: scripts/deploy_grafana.sh
Script should:
Check if Docker is running
Start Grafana container
Wait for Grafana to be healthy
Verify InfluxDB connection
Import dashboards via API
Set up alert channels
Print access URL and credentials
Run health check
Display summary of available dashboards
Step 7.3: Update Main README
Instructions for AI Agent:

Open file: docs/README.md
Add new section: "Grafana Dashboards"
Include:
Quick start command
Dashboard URLs
Default credentials
Link to full guide
PHASE 8: ADVANCED FEATURES (OPTIONAL)
Step 8.1: Trade Replay Feature
Instructions for AI Agent:

Add panel to Trade Verification dashboard:
Time slider to replay trade minute-by-minute
Show indicator values updating in real-time
Highlight when entry/exit conditions were met
Animated price chart
Step 8.2: AI-Powered Trade Insights
Instructions for AI Agent:

Create new file: src/analytics/trade_analyzer.py
For each trade, generate insights:
"Entry timing was optimal (RSI at perfect oversold level)"
"Exit was premature (target was hit 5 minutes later)"
"Stop loss was too tight (hit by -1.2% but then recovered)"
Store insights in InfluxDB
Display in Grafana as annotations
Step 8.3: Predictive Analytics Panel
Instructions for AI Agent:

Add panel to Strategy Performance dashboard:
Predict next trade outcome probability
Show confidence intervals
Based on current market conditions + indicator values
Use simple ML model (logistic regression)
Step 8.4: Mobile-Optimized Dashboard
Instructions for AI Agent:

Create simplified dashboard: velox-mobile.json
Designed for phone screens
Show only critical metrics:
P&L today
Open positions
Recent trade alerts
Quick action buttons
IMPLEMENTATION ORDER & TIMELINE
Day 1: Infrastructure (4 hours)

Phase 1: Steps 1.1 - 1.4
Day 2: Data Pipeline (6 hours)

Phase 2: Steps 2.1 - 2.4
Day 3: Main Dashboard (4 hours)

Phase 3: Dashboard 1
Day 4: Trade Verification (6 hours)

Phase 3: Dashboard 2
Day 5: Strategy & Risk Dashboards (6 hours)

Phase 3: Dashboards 3 & 4
Day 6: Alerting (4 hours)

Phase 4: Steps 4.1 - 4.2
Day 7: Dynamic Features (6 hours)

Phase 5: Steps 5.1 - 5.3
Day 8: Testing (4 hours)

Phase 6: Steps 6.1 - 6.3
Day 9: Documentation (4 hours)

Phase 7: Steps 7.1 - 7.3
Day 10: Polish & Launch (4 hours)

Final testing, screenshots, demo video
KEY SUCCESS METRICS
After implementation, verify:

✅ All dashboards load in < 2 seconds
✅ Data refreshes every 5-30 seconds (based on panel)
✅ Can verify any trade correctness in < 30 seconds
✅ All active strategies auto-detected and displayed
✅ Alerts trigger correctly for risk events
✅ 100% of indicator values captured at trade time
✅ Zero dashboard query errors
✅ Mobile-responsive (optional)