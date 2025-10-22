# Remaining Implementation Guide - Code Snippets

This document provides exact code snippets for implementing the remaining files.

---

## 🔴 CRITICAL: src/main.py

### Location: Find the `VeloxSystem` class

### Change 1: Add imports at top of file
```python
from .core.candle_aggregator import CandleAggregator
from .core.warmup_manager import WarmupManager
```

### Change 2: In `__init__` method, add these attributes:
```python
def __init__(self, config_path: str):
    # ... existing code ...
    
    # Add these new attributes
    self.candle_aggregator = None
    self.warmup_manager = None
    self.data_manager = DataManager()  # If not already present
```

### Change 3: In `run_simulation` method, add warmup logic BEFORE starting simulator:
```python
def run_simulation(self, date: str, symbols: List[str]):
    """Run trading simulation."""
    
    # ... existing initialization code ...
    
    # ========== NEW CODE: WARMUP & CANDLE AGGREGATION ==========
    
    # 1. Collect required timeframes from all strategies
    timeframes = set()
    for strategy in self.strategies:
        if hasattr(strategy, 'get_required_timeframes'):
            timeframes.update(strategy.get_required_timeframes())
        else:
            timeframes.add('1min')  # Default
    
    self.logger.info(f"Required timeframes: {timeframes}")
    
    # 2. Create CandleAggregator
    self.candle_aggregator = CandleAggregator(
        timeframes=list(timeframes),
        max_history=500
    )
    
    # 3. Register callbacks for candle completion
    for tf in timeframes:
        self.candle_aggregator.register_candle_callback(
            tf,
            lambda candle, tf=tf: self._on_candle_complete(candle)
        )
    
    # 4. Create WarmupManager
    self.warmup_manager = WarmupManager(
        min_candles=200,
        auto_calculate=True
    )
    
    # 5. Calculate required warmup period
    required_candles = self.warmup_manager.calculate_required_warmup(self.strategies)
    self.logger.info(f"Warmup requires {required_candles} candles")
    
    # 6. Load historical candles
    self.logger.info("Loading historical candles for warmup...")
    historical_candles = self.warmup_manager.load_historical_candles(
        data_manager=self.data_adapter,
        date=datetime.strptime(date, '%Y-%m-%d'),
        symbols=symbols,
        count=required_candles
    )
    
    if not historical_candles:
        self.logger.warning("No historical data for warmup - proceeding without warmup")
    else:
        # 7. Warmup strategies
        self.logger.info("Warming up strategies...")
        success = self.warmup_manager.warmup_strategies(
            strategies=self.strategies,
            historical_candles=historical_candles,
            candle_aggregator=self.candle_aggregator
        )
        
        if success:
            self.logger.info("✓ Warmup complete - ready for trading")
        else:
            self.logger.error("✗ Warmup failed - check logs")
    
    # 8. Attach candle aggregator to simulator
    self.simulator.set_candle_aggregator(self.candle_aggregator)
    
    # ========== END NEW CODE ==========
    
    # ... existing simulation start code ...
    self.simulator.run_simulation(callback_fn=self.process_tick)
```

### Change 4: Add new method to handle candle completion:
```python
def _on_candle_complete(self, candle):
    """
    Called when a candle completes.
    
    Args:
        candle: Completed Candle object
    """
    try:
        candle_data = candle.to_dict()
        
        # Notify all strategies
        for strategy in self.strategies:
            if hasattr(strategy, 'on_candle_complete'):
                strategy.on_candle_complete(candle_data, candle.timeframe)
        
        # Log to database
        if self.data_manager:
            self.data_manager.log_candle(
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                candle_data=candle_data,
                timestamp=candle.timestamp
            )
    except Exception as e:
        self.logger.error(f"Error in candle complete callback: {e}", exc_info=True)
```

### Change 5: Enhance `process_tick` method with database logging:
```python
def process_tick(self, tick_data: dict):
    """Process each tick (existing method - enhance with logging)."""
    
    # ... existing tick processing code ...
    
    # Add periodic database logging
    self.tick_count = getattr(self, 'tick_count', 0) + 1
    
    # Log position snapshots every 100 ticks
    if self.data_manager and self.tick_count % 100 == 0:
        for strategy in self.strategies:
            for symbol, position in strategy.positions.items():
                try:
                    current_price = tick_data.get('price', tick_data.get('close'))
                    entry_price = position.get('entry_price')
                    quantity = position.get('quantity')
                    
                    if entry_price and quantity:
                        unrealized_pnl = (current_price - entry_price) * quantity
                        
                        self.data_manager.log_position_update(
                            strategy_id=strategy.strategy_id,
                            symbol=symbol,
                            current_price=current_price,
                            quantity=quantity,
                            unrealized_pnl=unrealized_pnl,
                            timestamp=tick_data.get('timestamp')
                        )
                except Exception as e:
                    self.logger.error(f"Error logging position: {e}")
    
    # Log indicator values every 50 ticks
    if self.data_manager and self.tick_count % 50 == 0:
        symbol = tick_data.get('symbol')
        if symbol:
            try:
                # Get indicators from strategy's indicator manager
                for strategy in self.strategies:
                    if hasattr(strategy, 'indicator_manager'):
                        indicators = strategy.indicator_manager.get_indicators(symbol)
                        if indicators:
                            self.data_manager.log_indicator_values(
                                symbol=symbol,
                                indicators=indicators,
                                timestamp=tick_data.get('timestamp')
                            )
            except Exception as e:
                self.logger.error(f"Error logging indicators: {e}")
```

---

## 🟡 MEDIUM: src/core/order_manager.py

### Find the `OrderManager` class

### Change 1: Update `__init__` to accept data_manager:
```python
def __init__(self, broker, position_manager, risk_manager, data_manager=None):
    """Initialize order manager."""
    self.broker = broker
    self.position_manager = position_manager
    self.risk_manager = risk_manager
    self.data_manager = data_manager  # NEW
    self.logger = get_logger('order_manager')
```

### Change 2: Add trade ID generation method:
```python
def generate_trade_id(self, strategy_id: str, symbol: str, timestamp) -> str:
    """
    Generate unique trade ID.
    
    Args:
        strategy_id: Strategy identifier
        symbol: Symbol name
        timestamp: Trade timestamp
        
    Returns:
        Unique trade ID string
    """
    import hashlib
    from datetime import datetime
    
    if isinstance(timestamp, datetime):
        ts_str = timestamp.strftime('%Y%m%d_%H%M%S_%f')
    else:
        ts_str = str(timestamp)
    
    # Create unique ID
    unique_str = f"{strategy_id}_{symbol}_{ts_str}"
    trade_id = f"{strategy_id}_{symbol}_{ts_str[:15]}"
    
    return trade_id
```

### Change 3: Update `execute_signal` to log to database:
```python
def execute_signal(self, signal: dict):
    """Execute a trading signal."""
    
    # Log signal before execution
    if self.data_manager:
        try:
            self.data_manager.log_signal(
                signal_data=signal,
                approved=True,
                rejection_reason=None
            )
        except Exception as e:
            self.logger.error(f"Error logging signal: {e}")
    
    # ... existing execution code ...
    
    # If opening a position, generate and log trade_id
    if signal['action'] == 'BUY':
        trade_id = self.generate_trade_id(
            signal['strategy_id'],
            signal['symbol'],
            signal['timestamp']
        )
        
        # Log trade open
        if self.data_manager:
            try:
                self.data_manager.log_trade_open(
                    trade_id=trade_id,
                    strategy_id=signal['strategy_id'],
                    symbol=signal['symbol'],
                    entry_price=signal['price'],
                    quantity=signal['quantity'],
                    timestamp=signal['timestamp'],
                    signal_conditions=signal.get('indicators', {})
                )
            except Exception as e:
                self.logger.error(f"Error logging trade open: {e}")
        
        # Store trade_id in position for later reference
        # (You may need to modify position_manager to store this)
    
    # If closing a position, log trade close
    elif signal['action'] == 'SELL':
        # Get trade_id from position (if stored)
        # Calculate P&L
        # Log trade close
        if self.data_manager:
            try:
                # You'll need to get trade_id, entry_price from position
                # pnl = (exit_price - entry_price) * quantity
                # pnl_pct = (pnl / (entry_price * quantity)) * 100
                
                # self.data_manager.log_trade_close(
                #     trade_id=trade_id,
                #     exit_price=signal['price'],
                #     exit_time=signal['timestamp'],
                #     pnl=pnl,
                #     pnl_pct=pnl_pct,
                #     exit_reason=signal.get('reason', 'Unknown'),
                #     signal_conditions=signal.get('indicators', {})
                # )
                pass  # Implement based on your position structure
            except Exception as e:
                self.logger.error(f"Error logging trade close: {e}")
```

---

## 🟡 MEDIUM: src/core/risk_manager.py

### Find the `RiskManager` class

### Change 1: Update `__init__`:
```python
def __init__(self, config: dict, data_manager=None):
    """Initialize risk manager."""
    self.config = config
    self.data_manager = data_manager  # NEW
    self.logger = get_logger('risk_manager')
    # ... existing code ...
```

### Change 2: Update `validate_signal` to log:
```python
def validate_signal(self, signal: dict) -> tuple:
    """
    Validate a trading signal.
    
    Returns:
        (is_valid: bool, rejection_reason: str or None)
    """
    # ... existing validation logic ...
    
    is_valid = True
    rejection_reason = None
    
    # Your existing validation checks...
    # if some_check_fails:
    #     is_valid = False
    #     rejection_reason = "Reason for rejection"
    
    # Log validation result
    if self.data_manager:
        try:
            self.data_manager.log_signal(
                signal_data=signal,
                approved=is_valid,
                rejection_reason=rejection_reason
            )
        except Exception as e:
            self.logger.error(f"Error logging signal validation: {e}")
    
    return is_valid, rejection_reason
```

### Change 3: Add risk metrics method:
```python
def get_daily_risk_metrics(self) -> dict:
    """
    Get daily risk metrics.
    
    Returns:
        Dict with risk metrics
    """
    if self.data_manager:
        try:
            return self.data_manager.get_daily_summary()
        except Exception as e:
            self.logger.error(f"Error getting risk metrics: {e}")
    
    return {}

def get_rejection_statistics(self) -> dict:
    """
    Get statistics on signal rejections.
    
    Returns:
        Dict with rejection stats
    """
    # This would query the database for rejected signals
    # and aggregate by rejection reason
    if self.data_manager:
        try:
            # Implement based on your SQLite schema
            pass
        except Exception as e:
            self.logger.error(f"Error getting rejection stats: {e}")
    
    return {}
```

---

## 🟡 MEDIUM: src/core/trailing_sl.py

### Find the `TrailingStopLossManager` class

### Change 1: Update `__init__`:
```python
def __init__(self, config: dict, data_manager=None):
    """Initialize trailing stop loss manager."""
    self.config = config
    self.data_manager = data_manager  # NEW
    self.logger = get_logger('trailing_sl')
    # ... existing code ...
```

### Change 2: Update `add_stop_loss` to log:
```python
def add_stop_loss(self, trade_id: str, strategy_id: str, symbol: str, 
                  entry_price: float, atr: float, multiplier: float):
    """Add trailing stop loss for a position."""
    
    # ... existing logic to calculate initial SL ...
    
    # Log SL setup
    if self.data_manager:
        try:
            self.data_manager.update_trailing_sl(
                trade_id=trade_id,
                strategy_id=strategy_id,
                symbol=symbol,
                current_sl=initial_sl,
                highest_price=entry_price,
                sl_type='ATR_TRAILING'
            )
        except Exception as e:
            self.logger.error(f"Error logging SL setup: {e}")
```

### Change 3: Update `update_stop_loss` to log significant changes:
```python
def update_stop_loss(self, trade_id: str, strategy_id: str, symbol: str, 
                     current_price: float, highest_price: float):
    """Update trailing stop loss."""
    
    # ... existing logic to update SL ...
    
    # Get previous SL
    prev_sl = self.stop_losses.get(trade_id, {}).get('current_sl', 0)
    
    # Calculate new SL
    new_sl = highest_price - (atr * multiplier)
    
    # Only log if SL moved significantly (>0.1%)
    if prev_sl > 0:
        sl_change_pct = abs((new_sl - prev_sl) / prev_sl) * 100
        
        if sl_change_pct > 0.1 and self.data_manager:
            try:
                self.data_manager.update_trailing_sl(
                    trade_id=trade_id,
                    strategy_id=strategy_id,
                    symbol=symbol,
                    current_sl=new_sl,
                    highest_price=highest_price,
                    sl_type='ATR_TRAILING'
                )
            except Exception as e:
                self.logger.error(f"Error logging SL update: {e}")
```

---

## 🟢 LOW: config/system.yaml

### Add these sections to the YAML file:

```yaml
# Warmup Configuration
warmup:
  enabled: true
  min_candles: 200  # Minimum candles to load
  auto_calculate: true  # Auto-calculate from strategies

# Candle Aggregation Configuration
candle_aggregation:
  enabled: true
  default_timeframe: '1min'
  supported_timeframes:
    - '1min'
    - '3min'
    - '5min'
    - '15min'
  max_history: 500  # Max candles to keep per timeframe

# Database Logging Configuration
database_logging:
  log_all_signals: true  # Log approved and rejected signals
  log_all_ticks: false  # Warning: Can be expensive
  log_indicators: true  # Log indicator values
  log_candles: true  # Log completed candles
  position_snapshot_interval: 100  # Log position every N ticks
  indicator_snapshot_interval: 50  # Log indicators every N ticks
  batch_size: 50  # Batch size for bulk operations
```

---

## 🟢 LOW: src/utils/config_loader.py

### Add these methods to the `ConfigLoader` class:

```python
def get_warmup_config(self) -> dict:
    """
    Get warmup configuration.
    
    Returns:
        Dict with warmup settings
    """
    return self.config.get('warmup', {
        'enabled': True,
        'min_candles': 200,
        'auto_calculate': True
    })

def get_candle_aggregation_config(self) -> dict:
    """
    Get candle aggregation configuration.
    
    Returns:
        Dict with candle aggregation settings
    """
    return self.config.get('candle_aggregation', {
        'enabled': True,
        'default_timeframe': '1min',
        'supported_timeframes': ['1min', '3min', '5min', '15min'],
        'max_history': 500
    })

def get_database_logging_config(self) -> dict:
    """
    Get database logging configuration.
    
    Returns:
        Dict with logging settings
    """
    return self.config.get('database_logging', {
        'log_all_signals': True,
        'log_all_ticks': False,
        'log_indicators': True,
        'log_candles': True,
        'position_snapshot_interval': 100,
        'indicator_snapshot_interval': 50,
        'batch_size': 50
    })

def get_strategy_timeframes(self, strategy_id: str) -> list:
    """
    Get required timeframes for a strategy.
    
    Args:
        strategy_id: Strategy identifier
        
    Returns:
        List of timeframe strings
    """
    # Look in strategy config for timeframes
    strategies = self.config.get('strategies', {})
    strategy_config = strategies.get(strategy_id, {})
    
    return strategy_config.get('timeframes', ['1min'])
```

---

## 📝 QUICK IMPLEMENTATION CHECKLIST

Use this checklist to track your implementation:

- [ ] **main.py**
  - [ ] Add imports (CandleAggregator, WarmupManager)
  - [ ] Add attributes to __init__
  - [ ] Add warmup logic to run_simulation
  - [ ] Add _on_candle_complete method
  - [ ] Enhance process_tick with logging
  
- [ ] **order_manager.py**
  - [ ] Add data_manager to __init__
  - [ ] Add generate_trade_id method
  - [ ] Update execute_signal with logging
  
- [ ] **risk_manager.py**
  - [ ] Add data_manager to __init__
  - [ ] Update validate_signal with logging
  - [ ] Add get_daily_risk_metrics method
  
- [ ] **trailing_sl.py**
  - [ ] Add data_manager to __init__
  - [ ] Update add_stop_loss with logging
  - [ ] Update update_stop_loss with logging
  
- [ ] **system.yaml**
  - [ ] Add warmup section
  - [ ] Add candle_aggregation section
  - [ ] Add database_logging section
  
- [ ] **config_loader.py**
  - [ ] Add get_warmup_config method
  - [ ] Add get_candle_aggregation_config method
  - [ ] Add get_database_logging_config method

---

## 🧪 TESTING AFTER IMPLEMENTATION

After implementing the above changes, test with:

```bash
# 1. Test warmup
python -m src.main --date 2024-01-15 --symbols RELIANCE --test-warmup

# 2. Test candle aggregation
python -m src.main --date 2024-01-15 --symbols RELIANCE --test-candles

# 3. Test full simulation
python run_velox.py

# 4. Check database logs
python -c "from src.database.data_manager import DataManager; dm = DataManager(); print(dm.get_trade_history())"
```

---

**Good luck with the implementation!** 🚀

If you encounter any issues, refer back to the completed files for examples of the patterns used.
