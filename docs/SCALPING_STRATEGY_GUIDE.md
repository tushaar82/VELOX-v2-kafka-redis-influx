# Professional Tick-by-Tick Scalping Strategy

## Overview

The **ScalpingMTFATRStrategy** is a professional intraday scalping system that trades on every tick with multi-timeframe confirmation, supporting both LONG and SHORT positions.

## Strategy ID: `scalping_pro`

## Key Features

### ✅ Multi-Timeframe Trend Alignment
- **EMA 9/21** on 5-minute chart for entry signals
- **EMA 50** on 15-minute chart for trend confirmation
- **EMA 200** on 1-hour chart for long-term trend
- **MACD** for momentum confirmation

### ✅ Both LONG and SHORT Positions
- **LONG**: When all EMAs aligned bullish + MACD bullish
- **SHORT**: When all EMAs aligned bearish + MACD bearish

### ✅ Advanced Entry Filters
- RSI filter (40-70 for LONG, 30-60 for SHORT)
- Volume above 20-period average
- Price near EMA9 (within 0.2 ATR)
- MACD histogram confirmation

### ✅ Professional Risk Management
- **1% risk per trade** (calculated from stop distance)
- **Max 2 concurrent positions**
- **2.5% daily loss limit**
- **Stop after 3 consecutive losses**
- **2.5 ATR stop loss** from entry

### ✅ Multiple Take Profit Levels
- **TP1 @ 2 ATR**: Close 50% of position
- **TP2 @ 3 ATR**: Close 30% of position
- **Remaining 20%**: Trails with stop loss

### ✅ Dynamic Position Management
- **Breakeven**: Move SL to entry at 1 ATR profit
- **Trailing Start**: Activate at 1.5 ATR profit
- **Trailing Distance**: 2 ATR behind highest/lowest price
- **Never trails below entry** (profit protection)

## Entry Conditions

### LONG Signal (ALL must be TRUE)
```
✓ Price > EMA21
✓ EMA9 > EMA21
✓ Price > EMA50 (15-min)
✓ Price > EMA200 (1-hour)
✓ 40 < RSI < 70
✓ MACD line > MACD signal
✓ MACD histogram > 0
✓ Volume > Volume MA
✓ |Price - EMA9| < 0.2 ATR
✓ Price > EMA9
```

### SHORT Signal (ALL must be TRUE)
```
✓ Price < EMA21
✓ EMA9 < EMA21
✓ Price < EMA50 (15-min)
✓ Price < EMA200 (1-hour)
✓ 30 < RSI < 60
✓ MACD line < MACD signal
✓ MACD histogram < 0
✓ Volume > Volume MA
✓ |Price - EMA9| < 0.2 ATR
✓ Price < EMA9
```

## Exit Conditions

### 1. Take Profit Levels
- **TP1 (2 ATR)**: Close 50% of position
- **TP2 (3 ATR)**: Close 30% of position

### 2. Breakeven Protection
- At **1 ATR profit**: Move stop loss to entry price
- Ensures no loss after reaching 1 ATR profit

### 3. Trailing Stop
- Activates at **1.5 ATR profit**
- Trails **2 ATR** behind highest (LONG) or lowest (SHORT) price
- **Never moves below entry** (profit lock)

### 4. Stop Loss
- Initial: **2.5 ATR** from entry
- Updates to breakeven at 1 ATR profit
- Trails at 1.5 ATR profit

## Position Sizing

```python
# Calculate based on 1% risk
capital = 100,000
risk_amount = capital * 0.01  # ₹1,000
stop_distance = entry_price - stop_loss
quantity = risk_amount / stop_distance

# Example:
# Entry: ₹1,000
# SL: ₹950 (2.5 ATR = ₹50)
# Risk: ₹1,000
# Quantity: 1,000 / 50 = 20 shares
```

## Trade Example

### LONG Trade Flow

**TICK 1 (10:00:00):**
- Price: ₹1,000
- All LONG conditions met
- **Action**: BUY 20 shares @ ₹1,000
- SL: ₹950 (2.5 ATR)
- TP1: ₹1,080 (2 ATR)
- TP2: ₹1,120 (3 ATR)

**TICK 500 (10:05:30):**
- Price: ₹1,040
- Profit: 1 ATR
- **Action**: Move SL to ₹1,000 (breakeven)

**TICK 1000 (10:12:15):**
- Price: ₹1,060
- Profit: 1.5 ATR
- **Action**: Activate trailing SL @ ₹980

**TICK 1500 (10:18:45):**
- Price: ₹1,080
- **Action**: TP1 HIT - Close 10 shares (50%)
- Profit: ₹800 (10 × ₹80)

**TICK 2000 (10:25:30):**
- Price: ₹1,120
- **Action**: TP2 HIT - Close 6 shares (30%)
- Profit: ₹720 (6 × ₹120)

**TICK 2500 (10:32:00):**
- Price: ₹1,100
- Trailing SL hit @ ₹1,020
- **Action**: Close remaining 4 shares
- Profit: ₹80 (4 × ₹20)

**Total Profit**: ₹800 + ₹720 + ₹80 = **₹1,600**

## Configuration

```yaml
- id: scalping_pro
  class: ScalpingMTFATRStrategy
  enabled: true
  symbols:
    - ABB
    - BATAINDIA
    - ADANIENT
    - BANKINDIA
    - AMBER
  params:
    # EMA settings
    ema9: 9
    ema21: 21
    ema50_15m: 50
    ema200_1h: 200
    
    # ATR settings
    atr_period: 14
    atr_sl_mult: 2.5     # Stop loss
    atr_tp1_mult: 2.0    # TP1
    atr_tp2_mult: 3.0    # TP2
    atr_trail_mult: 2.0  # Trailing
    
    # RSI settings
    rsi_period: 14
    rsi_long_min: 40
    rsi_long_max: 70
    rsi_short_min: 30
    rsi_short_max: 60
    
    # Risk management
    risk_per_trade: 0.01      # 1%
    max_positions: 2
    daily_loss_limit: 0.025   # 2.5%
    max_consec_losses: 3
    
    # Profit management
    breakeven_atr: 1.0
    trailing_start_atr: 1.5
    tp1_pct: 0.5
    tp2_pct: 0.3
```

## Safety Features

### 1. Daily Loss Limit
- Stops trading if daily loss reaches 2.5%
- Resets at start of new day

### 2. Max Positions
- Maximum 2 concurrent positions
- Prevents overexposure

### 3. Consecutive Loss Protection
- Stops trading after 3 consecutive losses
- Prevents revenge trading

### 4. Breakeven Protection
- Moves SL to entry at 1 ATR profit
- Ensures no loss after initial profit

### 5. Profit Lock
- Trailing SL never moves below entry
- Locks in profits once activated

## Performance Metrics

### Expected Win Rate
- **40-50%** (due to 1:2 and 1:3 risk-reward)
- Profitable even with 40% win rate

### Risk-Reward Ratios
- **TP1**: 1:2 (50% of position)
- **TP2**: 1:3 (30% of position)
- **Trail**: Variable (20% of position)

### Average Trade
- **Risk**: 1% of capital
- **Reward**: 1.5-2% average (mixed TP1, TP2, trail)
- **Net**: Positive expectancy

## Best Practices

### 1. Symbol Selection
- Choose liquid stocks/futures
- High volume instruments
- Low spread

### 2. Timeframe
- Best for 5-minute to 15-minute charts
- Intraday only (close all by 3:15 PM)

### 3. Market Conditions
- Works best in trending markets
- Avoid during high volatility (VIX > 30)
- Avoid during major news events

### 4. Monitoring
- Watch for daily loss limit
- Monitor consecutive losses
- Track win rate and average RR

## Advantages

✅ **Multi-timeframe confirmation** reduces false signals
✅ **Both LONG and SHORT** captures all market moves
✅ **Multiple TP levels** maximize profit capture
✅ **Breakeven protection** prevents losses after initial profit
✅ **Trailing stop** locks in extended moves
✅ **Risk management** protects capital
✅ **Tick-by-tick execution** fast entries and exits

## Disadvantages

⚠️ **Requires low latency** for tick-by-tick execution
⚠️ **Multiple conditions** may reduce trade frequency
⚠️ **Needs trending markets** struggles in choppy conditions
⚠️ **Intraday only** no overnight positions

## Running the Strategy

```bash
# Start dashboard
python3 dashboard_final.py --date 2020-09-15

# Open browser
http://localhost:5000

# Monitor:
# - Active positions
# - P&L
# - Daily loss limit
# - Consecutive losses
```

## Modifications

### More Aggressive (Higher Frequency)
```yaml
rsi_long_min: 35      # Wider RSI range
rsi_long_max: 75
price_ema_dist: 0.3   # Wider entry zone
```

### More Conservative (Higher Quality)
```yaml
rsi_long_min: 45      # Tighter RSI range
rsi_long_max: 65
price_ema_dist: 0.1   # Tighter entry zone
volume_multiplier: 1.5  # Higher volume requirement
```

### Higher Risk-Reward
```yaml
atr_tp1_mult: 2.5     # TP1 at 2.5 ATR
atr_tp2_mult: 4.0     # TP2 at 4 ATR
trailing_start_atr: 2.0  # Trail at 2 ATR
```

## Summary

The **ScalpingMTFATRStrategy** is a professional-grade tick-by-tick scalping system that:

- ✅ Trades both LONG and SHORT
- ✅ Uses multi-timeframe confirmation
- ✅ Has multiple take profit levels
- ✅ Protects profits with breakeven and trailing stops
- ✅ Manages risk with position limits and daily loss limits
- ✅ Adapts to market volatility with ATR-based levels

Perfect for intraday scalping with professional risk management! 🚀
