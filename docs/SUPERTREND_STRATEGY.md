# Supertrend Strategy Implementation ✅

## Overview
Simple trend-following strategy using the Supertrend indicator on **3-minute candles**.

## Configuration

### Strategy Parameters (10, 3)
```yaml
strategies:
  - id: supertrend_simple
    class: SupertrendStrategy
    enabled: true
    symbols:
      - ABB
    params:
      atr_period: 10              # Supertrend ATR period
      atr_multiplier: 3           # Supertrend multiplier
      min_hold_time_minutes: 5    # Minimum 5 minutes hold
      min_volume: 50              # Minimum volume filter
```

### Timeframe
- **3-minute candles** (resampled from 1-minute data)
- 6 ticks per candle for smooth price action
- 100x simulation speed

## How Supertrend Works

### Calculation
```
HL_AVG = (High + Low) / 2
ATR = Average True Range (period: 10)

Upper Band = HL_AVG + (ATR × 3)
Lower Band = HL_AVG - (ATR × 3)

If Close > Supertrend:
    Trend = Bullish (use Lower Band)
Else:
    Trend = Bearish (use Upper Band)
```

### Entry Signal
**BUY when:**
- Price crosses **above** Supertrend line
- Trend changes from Bearish → Bullish
- Volume > minimum threshold

```
Previous: Bearish (price below Supertrend)
Current: Bullish (price above Supertrend)
→ BUY SIGNAL
```

### Exit Signal
**SELL when:**
- Price crosses **below** Supertrend line
- Trend changes from Bullish → Bearish
- After minimum hold time (5 minutes)

```
Previous: Bullish (price above Supertrend)
Current: Bearish (price below Supertrend)
→ SELL SIGNAL
```

## Example Trade

### Entry
```
[09:15:00] BUY SIGNAL: Supertrend turned bullish
  ├─ Price: $920.50
  ├─ Supertrend: $915.30
  └─ ATR: $13.75

Action: BUY ABB @ $920.50 x5
```

### During Trade
```
[09:18:00] Price: $925.00 (Supertrend: $917.50) ✅ Still bullish
[09:21:00] Price: $930.50 (Supertrend: $920.00) ✅ Still bullish
[09:24:00] Price: $928.00 (Supertrend: $922.50) ✅ Still bullish
```

### Exit
```
[09:27:00] SELL SIGNAL: Supertrend bearish crossover
  ├─ Entry: $920.50, Exit: $925.00
  ├─ P&L: +$4.50 (+0.49%)
  └─ Hold time: 12 minutes

Action: SELL ABB @ $925.00 x5
```

## Advantages

1. **Simple & Clear**: Only two signals (bullish/bearish crossover)
2. **Trend Following**: Catches sustained moves
3. **Adaptive**: ATR adjusts to volatility
4. **Easy to Test**: Clear entry/exit rules
5. **Visual**: Can plot Supertrend line on chart

## Testing Benefits

### Why Supertrend for Testing?
- ✅ **Simple logic**: Easy to verify signals
- ✅ **Clear signals**: No ambiguity in entry/exit
- ✅ **One symbol**: Focus on ABB only
- ✅ **3-min candles**: Fewer signals, easier to track
- ✅ **Standard parameters**: 10, 3 are well-tested values

### What to Watch
```
[INFO] ✅ Loaded strategy: supertrend_simple (ABB)
[INFO]    Target: 0.0%, SL: 0.0%, Min Hold: 5min
[INFO] Loading 3-minute candle data for 2020-09-15...
[INFO] Resampled to 130 3-minute candles
[INFO] Using 3-minute candles: 130 candles loaded
```

### Expected Signals
```
[INFO] [ABB] BUY SIGNAL: Supertrend turned bullish
  ├─ Price: 920.50
  ├─ Supertrend: 915.30
  └─ ATR: 13.75

[INFO] [ABB] SELL SIGNAL: Supertrend bearish crossover: 925.00 < 922.50 (P&L: +0.49%)
  ├─ Entry: 920.50, Exit: 925.00
  ├─ P&L: +0.49%
  └─ Hold time: 12.0 min
```

## Files Modified

### New Files
- `src/adapters/strategy/supertrend.py` - Supertrend strategy implementation

### Updated Files
- `config/strategies.yaml` - Removed RSI strategies, added Supertrend
- `src/utils/strategy_loader.py` - Added SupertrendStrategy to loader
- `dashboard_working.py` - Added 3-minute candle resampling
- `start_velox.sh` - Updated for Supertrend strategy

## Running the Strategy

### Start Dashboard
```bash
./start_velox.sh
```

### What You'll See
```
🚀 VELOX TRADING SYSTEM - STARTUP (v2.1 - Supertrend Strategy)
====================================================================
📊 Dashboard: http://localhost:5000
📅 Date: 2020-09-15
⚡ Speed: 100x (realistic simulation)
⏱️  Timeframe: 3-minute candles
📈 Strategy: Supertrend (10, 3)
   • ATR Period: 10
   • ATR Multiplier: 3
   • Symbol: ABB
   • Min Hold: 5 minutes
====================================================================

What to expect:
  • Supertrend strategy on 3-minute candles
  • BUY when price crosses above Supertrend (bullish)
  • SELL when price crosses below Supertrend (bearish)
  • Simple trend-following with clear signals
```

## Customization

### Change Parameters
Edit `config/strategies.yaml`:

```yaml
params:
  atr_period: 14        # Longer period = smoother
  atr_multiplier: 2     # Tighter bands = more signals
  min_hold_time_minutes: 10  # Longer holds
```

### Add More Symbols
```yaml
symbols:
  - ABB
  - BATAINDIA
  - RELIANCE
```

### Change Timeframe
In `dashboard_working.py`, change:
```python
resampled = symbol_data.resample('5T').agg({  # 5-minute candles
```

## Comparison: RSI vs Supertrend

### RSI Strategy (Previous)
- Multiple indicators (RSI, MA)
- Multiple exit conditions (target, RSI overbought, trailing SL)
- More parameters to tune
- Complex logic

### Supertrend Strategy (Current)
- Single indicator (Supertrend)
- Single exit condition (trend reversal)
- Two parameters (period, multiplier)
- Simple logic

**Result**: Easier to test, debug, and understand!

## Next Steps

1. **Run the simulation**: `./start_velox.sh`
2. **Watch for signals**: Look for BUY/SELL in logs
3. **Verify logic**: Check if signals make sense
4. **Adjust parameters**: Try different ATR period/multiplier
5. **Add symbols**: Test on multiple stocks

---

**Simple Supertrend strategy ready for testing!** 🎉
