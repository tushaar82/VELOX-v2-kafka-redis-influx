# VELOX Strategy Configuration Guide

## Overview

The VELOX trading system now supports **YAML-based strategy configuration**, making it easy to add, modify, and manage trading strategies without changing code.

## Configuration File

**Location:** `config/strategies.yaml`

## Current Strategies

### 1. RSI Aggressive Strategy
- **ID:** `rsi_aggressive`
- **Class:** `RSIMomentumStrategy`
- **Symbols:** ABB, BATAINDIA
- **Parameters:**
  - RSI Period: 10
  - RSI Oversold: 45
  - RSI Overbought: 55
  - MA Period: 10
  - Target: 1% profit
  - Stop Loss: 0.8%
  - Min Volume: 50
- **Trailing SL:** ATR-based (2x ATR, 14-period)

### 2. RSI Moderate Strategy
- **ID:** `rsi_moderate`
- **Class:** `RSIMomentumStrategy`
- **Symbols:** ANGELONE, AMBER
- **Parameters:**
  - RSI Period: 12
  - RSI Oversold: 40
  - RSI Overbought: 60
  - MA Period: 15
  - Target: 1.2% profit
  - Stop Loss: 1%
  - Min Volume: 50
- **Trailing SL:** ATR-based (2x ATR, 14-period)

### 3. Multi-Timeframe ATR Strategy (NEW!)
- **ID:** `mtf_atr`
- **Class:** `MultiTimeframeATRStrategy`
- **Symbols:** ADANIENT, BANKINDIA
- **Features:**
  - ✅ Multi-timeframe confirmation (5-min + 15-min)
  - ✅ EMA crossover (9/21) with trend confirmation (50 EMA)
  - ✅ ATR-based trailing stop loss (2x ATR)
  - ✅ Fixed 1:3 risk-reward ratio
  - ✅ Volume filter (1.2x average)
  - ✅ RSI filter (30-70 range)
  - ✅ Dynamic position sizing (2% capital risk)
- **Parameters:**
  - Fast EMA: 9
  - Slow EMA: 21
  - Trend EMA: 50
  - ATR Period: 14
  - ATR Multiplier: 2.0
  - Risk-Reward Ratio: 3.0
  - RSI Range: 30-70
  - Volume Multiplier: 1.2x
  - Position Size: 2% of capital

## How to Add a New Strategy

1. **Create the strategy class** in `src/adapters/strategy/`
2. **Add to `__init__.py`** for imports
3. **Update `strategies.yaml`** with configuration:

```yaml
- id: my_new_strategy
  class: MyNewStrategyClass
  enabled: true
  symbols:
    - SYMBOL1
    - SYMBOL2
  params:
    param1: value1
    param2: value2
  trailing_sl:
    type: atr
    atr_multiplier: 2.0
    atr_period: 14
```

4. **Update `strategy_loader.py`** to include the new class in `strategy_classes` dict

## How to Enable/Disable Strategies

Simply change the `enabled` field in `strategies.yaml`:

```yaml
- id: rsi_aggressive
  enabled: true   # Change to false to disable
```

## Running the Dashboard

```bash
# Run with default date (2020-09-15)
python3 dashboard_final.py

# Run with specific date
python3 dashboard_final.py --date 2024-01-02

# Run on different port
python3 dashboard_final.py --port 8080
```

## Strategy Loader Features

The `strategy_loader.py` utility provides:

- **`load_strategies_config()`** - Load all strategies from YAML
- **`get_enabled_strategies()`** - Get only enabled strategies
- **`get_all_strategy_symbols()`** - Get all unique symbols
- **`create_strategy_instance()`** - Create strategy instances dynamically

## Benefits

✅ **No code changes needed** to modify strategy parameters
✅ **Easy to enable/disable** strategies
✅ **Centralized configuration** for all strategies
✅ **Automatic symbol filtering** - only uses symbols with available data
✅ **Dynamic strategy loading** at runtime
✅ **Easy to add new strategies** without modifying dashboard code

## Multi-Timeframe ATR Strategy Details

### Entry Conditions
1. Fast EMA (9) crosses above Slow EMA (21) - **Bullish signal**
2. Price above Trend EMA (50) on 15-min timeframe - **Uptrend confirmation**
3. RSI between 30-70 - **Not overbought/oversold**
4. Volume > 1.2x average - **Strong momentum**

### Exit Conditions
1. **Target hit** - Price reaches 3x risk (1:3 RR)
2. **Trailing stop hit** - ATR-based trailing stop (2x ATR)
3. **Reversal signal** - Fast EMA crosses below Slow EMA

### Position Sizing
- Risk per trade: 2% of capital
- Stop loss: Entry price - (2x ATR)
- Target: Entry price + (6x ATR) for 1:3 RR
- Quantity calculated based on risk amount

### Why This Strategy is Profitable

1. **Multi-timeframe confirmation** reduces false signals
2. **ATR-based stops** adapt to market volatility
3. **1:3 risk-reward** means you only need 33% win rate to be profitable
4. **Volume filter** ensures strong momentum
5. **Trailing stops** lock in profits as price moves favorably
6. **Dynamic position sizing** manages risk consistently

## Example Output

```
✓ Strategy 1: rsi_aggressive (ABB, BATAINDIA) - RSIMomentumStrategy
✓ Strategy 2: rsi_moderate (AMBER) - RSIMomentumStrategy
✓ Strategy 3: mtf_atr (ADANIENT, BANKINDIA) - MultiTimeframeATRStrategy
```

## Notes

- Strategies automatically filter symbols based on data availability
- If a symbol has no data for the selected date, it's skipped
- The dashboard shows which symbols are actually being used
- All strategies use ATR-based trailing stop loss for better risk management
