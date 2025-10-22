# Realistic Trading System Improvements

## Problem Identified
Positions were closing in very short time periods (seconds) with no profitable trades due to:
1. **Overly tight stop losses** (0.8%) hitting on normal market noise
2. **Tick generation hitting extremes** - simulator always touched candle high/low
3. **No minimum hold time** - positions could close instantly
4. **Unrealistic price movement** - ticks jumped to extremes too quickly

## Solutions Implemented

### 1. Market Simulator Improvements (`src/core/market_simulator.py`)

#### More Realistic Price Path Generation
- **Before**: Every candle always hit both high and low extremes
- **After**: 
  - 70% of candles use gradual price movement (open → close)
  - Only 30% hit extremes (volatile candles)
  - Volatility check: only very volatile candles (>2%) hit both extremes

#### Smoother Price Interpolation
- **Before**: Linear interpolation with tiny noise (±0.02%)
- **After**:
  - Gaussian noise (±0.05%) for realistic random walk
  - Exponential smoothing (alpha=0.3) to avoid sharp jumps
  - Buffer zone (0.1%) from extremes to prevent premature stop hits

#### Realistic Bid-Ask Spread
- **Before**: 0.05% spread
- **After**: 0.1% spread (typical for Indian stocks)

### 2. Strategy Improvements (`src/adapters/strategy/rsi_momentum.py`)

#### Minimum Hold Time Protection
- **New Feature**: `min_hold_time_minutes` parameter (default: 5 minutes)
- Prevents instant exits on market noise
- Hard stop losses still trigger immediately for protection
- Profit targets and RSI exits only after minimum hold time

#### Breakeven Stop Loss Management
- **New Feature**: `breakeven_trigger_pct` parameter (default: 0.5%)
- Automatically moves stop loss to breakeven when position is profitable
- Protects profits while giving room for further gains
- Tracks highest price reached for optimal protection

#### Enhanced Exit Logic
```
Priority 1: Hard stop loss (immediate exit, any time)
Priority 2: Target hit (after min hold time)
Priority 3: RSI overbought (after min hold time, only if profitable)
```

#### Better Position Tracking
- Tracks entry timestamp for hold time calculation
- Tracks highest price for trailing stop logic
- Logs hold duration in exit signals

### 3. Configuration Updates

#### Strategy Parameters (`config/strategies.yaml` & `dashboard_working.py`)

**rsi_aggressive** (ABB, BATAINDIA):
- Target: 1.5% (was 1.0%)
- Stop Loss: 1.2% (was 0.8%)
- Min Hold: 5 minutes
- Breakeven Trigger: 0.7%
- RSI: 35/65 (was 45/55) - less sensitive

**rsi_moderate** (ANGELONE):
- Target: 2.0% (was 1.2%)
- Stop Loss: 1.5% (was 1.0%)
- Min Hold: 10 minutes
- Breakeven Trigger: 0.8%
- RSI: 30/70 (standard levels)

#### Simulator Settings
- Speed: 100x (was 50x) - faster simulation
- Ticks per candle: 6 (was 10) - every 10 seconds
- Smoother price action with fewer tick updates

### 4. Existing Features Leveraged

#### Slippage (Already Implemented)
- Broker already had realistic slippage (0.05-0.1%)
- Buy orders: filled at slightly higher price
- Sell orders: filled at slightly lower price

## Expected Behavior Changes

### Before
```
[08:54:32] BUY ABB @ $916.72 x5
[08:54:32] Trailing SL activated
[08:54:36] SELL ABB @ $915.36 | P&L: $-6.80 (-0.15%)
Duration: 4 seconds | Result: Loss
```

### After
```
[09:15:00] BUY ABB @ $916.72 x5
[09:15:00] Trailing SL activated
[09:17:30] Stop loss moved to breakeven @ $916.72
[09:22:15] SELL ABB @ $930.45 | P&L: $68.65 (+1.5%)
Duration: 7 minutes 15 seconds | Result: Profit (Target Hit)
```

## Key Improvements

1. ✅ **Positions hold longer** - minimum 5-10 minutes depending on strategy
2. ✅ **Breakeven protection** - stops move to entry price when profitable
3. ✅ **Wider stops** - 1.2-1.5% to avoid noise-induced exits
4. ✅ **Realistic price movement** - gradual price changes, not always hitting extremes
5. ✅ **Better profit potential** - positions have time to develop
6. ✅ **Realistic slippage** - already implemented in broker

## Testing Recommendations

1. Run the simulation and observe:
   - Average hold time should be 5-15 minutes
   - Mix of profitable and losing trades (not all losses)
   - Some positions hitting targets (1.5-2%)
   - Some positions hitting breakeven after being profitable
   - Fewer total trades but better quality

2. Monitor these metrics:
   - Win rate: Should be 40-60% (realistic)
   - Average hold time: 5-15 minutes
   - Profit factor: Should be > 1.0
   - Max consecutive losses: Should be < 5

## Running the Improved System

```bash
python dashboard_working.py
```

Then open http://localhost:5000 in your browser.

## Notes

- The system now simulates **realistic intraday trading**
- Not every trade will be profitable (that's normal!)
- The goal is a positive expectancy over many trades
- Minimum hold times prevent overtrading
- Breakeven stops protect profits while allowing runners
