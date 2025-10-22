# Dashboard Now Reads from YAML Config! ✅

## Problem Fix
`dashboard_working.py` was using **hardcoded strategy parameters** instead of reading from `config/strategies.yaml`.

## Changes Made

### 1. Added Config Loader Import
```python
from src.utils.strategy_loader import (
    load_strategies_config,
    get_enabled_strategies,
    create_strategy_instance,
    get_all_strategy_symbols
)
```

### 2. Load Strategies from YAML
**Before (Hardcoded):**
```python
strategy1 = RSIMomentumStrategy('rsi_aggressive', ['ABB', 'BATAINDIA'], {
    'rsi_period': 14,
    'rsi_oversold': 35,
    # ... hardcoded parameters
})
```

**After (From Config):**
```python
# Load from YAML
strategy_configs = get_enabled_strategies('./config/strategies.yaml')

# Create strategies dynamically
for config in strategy_configs:
    strategy = create_strategy_instance(config, all_symbols)
    strategy.initialize()
    strategy_manager.add_strategy(strategy)
```

### 3. Dynamic Symbol Loading
```python
# Get all symbols from enabled strategies
all_symbols = get_all_strategy_symbols('./config/strategies.yaml')
# Uses: ['ABB', 'BATAINDIA', 'ANGELONE', 'AMBER']
```

### 4. Trailing SL Config from YAML
```python
# Read trailing SL multiplier from config
for strat_config in strategy_configs:
    if strat_config['id'] == signal['strategy_id']:
        trailing_config = strat_config.get('trailing_sl', {})
        atr_multiplier = trailing_config.get('atr_multiplier', 2.5)
```

## What This Means

### ✅ Now You Can Edit `config/strategies.yaml` and Changes Apply!

**Example: Change Target Percentage**
```yaml
# In config/strategies.yaml
params:
  target_pct: 0.02  # Change from 1.5% to 2%
```
Restart dashboard → New target is used!

**Example: Add New Symbol**
```yaml
symbols:
  - ABB
  - BATAINDIA
  - RELIANCE  # Add new symbol
```
Restart dashboard → RELIANCE is now traded!

**Example: Adjust Trailing SL**
```yaml
trailing_sl:
  atr_multiplier: 3.0  # Change from 2.5 to 3.0
```
Restart dashboard → Wider trailing stop!

**Example: Enable/Disable Strategy**
```yaml
- id: rsi_aggressive
  enabled: false  # Disable this strategy
```
Restart dashboard → Strategy won't run!

## Log Messages

You'll now see:
```
[INFO] Loading strategies from config/strategies.yaml...
[INFO] Found 2 enabled strategies
[INFO] Symbols required: ABB, ANGELONE, AMBER, BATAINDIA
[INFO] ✅ Loaded strategy: rsi_aggressive (ABB, BATAINDIA)
[INFO]    Target: 1.5%, SL: 1.2%, Min Hold: 5min
[INFO] ✅ Loaded strategy: rsi_moderate (ANGELONE, AMBER)
[INFO]    Target: 2.0%, SL: 1.5%, Min Hold: 10min
```

## Benefits

1. ✅ **Single source of truth**: All config in YAML files
2. ✅ **No code changes needed**: Just edit YAML and restart
3. ✅ **Easy testing**: Try different parameters without touching code
4. ✅ **Version control**: Track config changes in git
5. ✅ **Multiple strategies**: Add/remove strategies easily

## How to Use

### 1. Edit Config
```bash
nano config/strategies.yaml
# or
vim config/strategies.yaml
```

### 2. Restart Dashboard
```bash
./start_velox.sh
# or
python3 dashboard_working.py
```

### 3. Changes Applied!
The dashboard will load your new settings automatically.

## Config File Structure

```yaml
strategies:
  - id: strategy_name          # Unique identifier
    class: RSIMomentumStrategy  # Strategy class
    enabled: true               # Enable/disable
    symbols:                    # Symbols to trade
      - ABB
      - BATAINDIA
    params:                     # Strategy parameters
      rsi_period: 14
      target_pct: 0.015
      initial_sl_pct: 0.012
      min_hold_time_minutes: 5
      # ... all parameters
    trailing_sl:                # Trailing SL config
      type: atr
      atr_multiplier: 2.5
      atr_period: 14
```

## Testing Different Configs

### Conservative Setup
```yaml
params:
  target_pct: 0.025      # 2.5% target
  initial_sl_pct: 0.02   # 2% stop loss
  min_hold_time_minutes: 15
trailing_sl:
  atr_multiplier: 3.5    # Wider trailing
```

### Aggressive Setup
```yaml
params:
  target_pct: 0.01       # 1% target
  initial_sl_pct: 0.008  # 0.8% stop loss
  min_hold_time_minutes: 3
trailing_sl:
  atr_multiplier: 2.0    # Tighter trailing
```

## Troubleshooting

### If strategies don't load:
1. Check YAML syntax (indentation matters!)
2. Ensure `enabled: true` for strategies you want
3. Check symbols have data available
4. Look for error messages in logs

### Validate YAML:
```bash
python3 -c "import yaml; yaml.safe_load(open('config/strategies.yaml'))"
```

---

**Your dashboard now reads all settings from YAML config files!** 🎉
