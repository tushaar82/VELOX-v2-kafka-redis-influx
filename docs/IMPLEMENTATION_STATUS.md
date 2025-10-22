# VELOX Candle Aggregation & Warmup Implementation Status

## ✅ COMPLETED (High Priority - Core Infrastructure)

### 1. **src/core/candle_aggregator.py** ✓
- Created complete `CandleAggregator` class
- Supports multiple timeframes (1min, 3min, 5min, 15min, 30min, 1hour, 1day)
- Maintains forming candles that update with every tick
- Emits completed candles via callbacks
- Stores historical closed candles (configurable max history)
- Methods: `process_tick()`, `get_closed_candles()`, `get_forming_candle()`, `get_candle_state()`, `register_candle_callback()`, `add_historical_candle()`

### 2. **src/core/warmup_manager.py** ✓
- Created complete `WarmupManager` class
- Calculates required warmup period from strategies
- Loads historical candles before simulation
- Feeds candles to strategies without generating signals
- Tracks warmup progress (percentage, candles loaded/required)
- Methods: `calculate_required_warmup()`, `load_historical_candles()`, `warmup_strategies()`, `mark_warmup_complete()`, `get_warmup_status()`

### 3. **src/adapters/strategy/base.py** ✓
- Added `is_warmed_up` flag (default False)
- Added `warmup_candles_required` property (default 200)
- Added `on_warmup_candle()` method for historical candle processing
- Added `on_candle_complete()` method for closed candle events
- Added `get_required_timeframes()` method
- Added `set_warmup_complete()` method
- Updated `get_status()` to include warmup info
- Updated `on_tick()` docstring to mention warmup check

### 4. **src/adapters/strategy/supertrend.py** ✓
- Set `warmup_candles_required = max(atr_period + 1, 50)`
- Implemented `on_warmup_candle()` - feeds candles to indicator manager
- Implemented `on_candle_complete()` - recalculates Supertrend on candle close
- Updated `on_tick()` to check `is_warmed_up` before generating signals
- Updated `on_tick()` to use `update_forming_candle()` if available
- Added warmup check in `check_entry_conditions()` and `check_exit_conditions()`
- Updated `get_status()` to call parent class method

### 5. **src/adapters/strategy/rsi_momentum.py** ✓
- Set `warmup_candles_required = max(rsi_period, ma_period) + 10`
- Implemented `on_warmup_candle()` - feeds candles to indicator manager
- Implemented `on_candle_complete()` - recalculates indicators on candle close
- Updated `on_tick()` to check `is_warmed_up` before generating signals
- Updated `on_tick()` to use `update_forming_candle()` if available
- Added warmup check in `check_entry_conditions()` and `check_exit_conditions()`

### 6. **src/utils/indicators.py** ✓
- Added `open_prices` deque to `TechnicalIndicators`
- Added `forming_candle` attribute for current forming candle
- Added `add_candle()` method for complete OHLC candles
- Added `update_forming_candle()` method for real-time updates
- Added `get_candle_count()` method
- Added `is_ready()` method to check if enough data exists
- Added `get_all_with_forming()` method for real-time indicator calculation
- Added `add_candle()` method to `IndicatorManager`
- Added `update_forming_candle()` method to `IndicatorManager`
- Added `process_candle()` method to `IndicatorManager`
- Added `get_candle_count()` and `is_ready()` methods to `IndicatorManager`

### 7. **src/core/market_simulator.py** ✓
- Added `candle_aggregator` attribute (optional)
- Added `set_candle_aggregator()` method
- Updated `run_simulation()` to process ticks through aggregator if set
- Maintains backward compatibility (works with or without aggregator)
- Updated docstring to explain candle aggregation flow

---

## ⏳ REMAINING IMPLEMENTATION (To Be Completed)

### HIGH PRIORITY

#### 8. **src/main.py** (CRITICAL - Orchestrates Everything)
**Status:** NOT STARTED

**Required Changes:**
```python
# Add imports
from .core.candle_aggregator import CandleAggregator
from .core.warmup_manager import WarmupManager

class VeloxSystem:
    def __init__(self, ...):
        # Add new components
        self.candle_aggregator = None
        self.warmup_manager = None
        self.data_manager = DataManager(...)  # Unified database manager
    
    def run_simulation(self, ...):
        # 1. Collect required timeframes from all strategies
        timeframes = set()
        for strategy in self.strategies:
            timeframes.update(strategy.get_required_timeframes())
        
        # 2. Create CandleAggregator
        self.candle_aggregator = CandleAggregator(
            timeframes=list(timeframes),
            max_history=500
        )
        
        # 3. Register callbacks for candle completion
        for tf in timeframes:
            self.candle_aggregator.register_candle_callback(
                tf, 
                lambda candle: self._on_candle_complete(candle)
            )
        
        # 4. Create WarmupManager
        self.warmup_manager = WarmupManager(
            min_candles=200,
            auto_calculate=True
        )
        
        # 5. Calculate required warmup
        required_candles = self.warmup_manager.calculate_required_warmup(self.strategies)
        
        # 6. Load historical candles
        historical_candles = self.warmup_manager.load_historical_candles(
            data_manager=self.data_adapter,
            date=self.simulation_date,
            symbols=self.symbols,
            count=required_candles
        )
        
        # 7. Warmup strategies
        self.warmup_manager.warmup_strategies(
            strategies=self.strategies,
            historical_candles=historical_candles,
            candle_aggregator=self.candle_aggregator
        )
        
        # 8. Set candle aggregator on simulator
        self.simulator.set_candle_aggregator(self.candle_aggregator)
        
        # 9. Start simulation
        self.simulator.run_simulation(callback_fn=self.process_tick)
    
    def _on_candle_complete(self, candle):
        """Called when a candle completes"""
        candle_data = candle.to_dict()
        
        # Notify all strategies
        for strategy in self.strategies:
            strategy.on_candle_complete(candle_data, candle.timeframe)
        
        # Log to database
        if self.data_manager:
            self.data_manager.log_candle(
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                candle_data=candle_data,
                timestamp=candle.timestamp
            )
    
    def process_tick(self, tick_data):
        """Process each tick (existing method - enhance with logging)"""
        # Existing tick processing...
        
        # Add database logging
        if self.data_manager:
            # Log position snapshots periodically
            if self.tick_count % 100 == 0:
                self.data_manager.log_position_snapshot(...)
            
            # Log indicator values periodically
            if self.tick_count % 50 == 0:
                self.data_manager.log_indicator_values(...)
```

---

### MEDIUM PRIORITY

#### 9. **dashboard_integrated.py**
**Status:** NOT STARTED

**Required Changes:**
- Add `candle_aggregator` and `warmup_manager` to simulation setup
- Display warmup status in UI (progress bar, candles loaded/required)
- Show current forming candle for each symbol
- Display indicator readiness status
- Add `/api/warmup_status` endpoint
- Add `/api/candles/<symbol>` endpoint
- Enhance database logging throughout
- Add error handling for all database operations

#### 10. **src/database/data_manager.py**
**Status:** NOT STARTED

**Required Methods to Add:**
```python
def log_signal(self, signal_data, approved, rejection_reason=None):
    """Log all signals (approved and rejected)"""

def log_trade_open(self, trade_id, strategy_id, symbol, entry_price, quantity, timestamp, signal_conditions):
    """Log trade opening"""

def log_trade_close(self, trade_id, exit_price, exit_time, pnl, pnl_pct, exit_reason, signal_conditions):
    """Log trade closing"""

def log_position_update(self, strategy_id, symbol, current_price, quantity, unrealized_pnl, timestamp):
    """Log position snapshots"""

def log_indicator_values(self, symbol, indicators, timestamp):
    """Log indicator snapshots"""

def log_candle(self, symbol, timeframe, candle_data, timestamp):
    """Log candle data"""

def batch_log_ticks(self, ticks):
    """Batch log ticks for performance"""

def batch_log_indicators(self, indicators):
    """Batch log indicators"""

def get_trade_history(self, strategy_id, limit=100):
    """Retrieve trade history"""

def get_performance_metrics(self, strategy_id, date_range):
    """Get performance analytics"""
```

#### 11. **src/core/order_manager.py**
**Status:** NOT STARTED

**Required Changes:**
- Add `data_manager` parameter to constructor (optional)
- Add `generate_trade_id()` method
- Modify `execute_signal()` to log signals and trades to database
- Wrap all database operations in try-except

#### 12. **src/core/risk_manager.py**
**Status:** NOT STARTED

**Required Changes:**
- Add `data_manager` parameter to constructor (optional)
- Modify `validate_signal()` to log validation attempts
- Add `log_risk_event()` method
- Add `get_daily_risk_metrics()` and `get_rejection_statistics()` methods

#### 13. **src/core/trailing_sl.py**
**Status:** NOT STARTED

**Required Changes:**
- Add `data_manager` parameter to constructor (optional)
- Log SL setup, updates, and hits to database
- Add `get_sl_history()` method

---

### LOW PRIORITY

#### 14. **config/system.yaml**
**Status:** NOT STARTED

**Required Additions:**
```yaml
warmup:
  enabled: true
  min_candles: 200
  auto_calculate: true

candle_aggregation:
  enabled: true
  default_timeframe: '1min'
  supported_timeframes: ['1min', '3min', '5min', '15min']

database_logging:
  log_all_signals: true
  log_all_ticks: false  # Can be expensive
  log_indicators: true
  position_snapshot_interval: 100  # ticks
  batch_size: 50
```

#### 15. **src/utils/config_loader.py**
**Status:** NOT STARTED

**Required Methods:**
```python
def get_warmup_config(self):
    """Get warmup configuration"""

def get_candle_aggregation_config(self):
    """Get candle aggregation configuration"""

def get_database_logging_config(self):
    """Get database logging configuration"""

def get_strategy_timeframes(self, strategy_id):
    """Get required timeframes for a strategy"""
```

#### 16. **src/dashboard/templates/dashboard.html**
**Status:** NOT STARTED

**Required Additions:**
- Warmup Status section (progress bar, candles loaded/required, ETA)
- Current Candles section (forming candle OHLC, time remaining)
- Indicators section (current values, readiness status)
- Database Status section (connection status, records logged)
- Enhanced positions table (trade ID, trailing SL, unrealized P&L)
- Error messages display area

#### 17. **README.md**
**Status:** NOT STARTED

**Required Sections:**
- Historical Warmup explanation
- Candle Aggregation explanation
- Database Logging explanation
- Updated Quick Start with warmup phase
- Troubleshooting section

---

### TEST FILES

#### 18. **tests/test_candle_aggregator.py**
**Status:** NOT STARTED

**Test Coverage:**
- Tick-to-candle aggregation for multiple timeframes
- Forming candle updates
- Candle completion detection
- Multiple symbols simultaneously
- Edge cases (first tick, market boundaries, gaps, out-of-order)
- Callback registration and invocation
- OHLC and volume calculations

#### 19. **tests/test_warmup.py**
**Status:** NOT STARTED

**Test Coverage:**
- Loading historical candles
- Calculating required warmup period
- Feeding candles to strategies without signals
- Warmup progress tracking
- Marking warmup complete
- Indicator initialization after warmup
- Edge cases (insufficient data, different requirements)

#### 20. **tests/test_database_logging.py**
**Status:** NOT STARTED

**Test Coverage:**
- Logging signals (approved/rejected)
- Logging trades (open/close)
- Logging position snapshots
- Logging indicator values
- Caching in Redis
- Graceful degradation when databases unavailable
- Batch logging performance
- Data consistency across databases

---

## INTEGRATION NOTES

### Critical Integration Points:

1. **main.py → All Components**
   - Orchestrates warmup → candle aggregation → trading flow
   - Must initialize components in correct order
   - Must handle errors gracefully

2. **Strategies → Indicator Manager**
   - Strategies call `add_candle()` during warmup
   - Strategies call `update_forming_candle()` during live trading
   - Must check `is_warmed_up` before generating signals

3. **MarketSimulator → CandleAggregator**
   - Simulator passes ticks to aggregator
   - Aggregator emits completed candles via callbacks
   - Maintains backward compatibility

4. **DataManager → All Components**
   - Unified interface for all database operations
   - Must handle failures gracefully (try-except everywhere)
   - Should not break trading if database fails

### Testing Strategy:

1. **Unit Tests First:** Test each component in isolation
2. **Integration Tests:** Test warmup → aggregation → strategy flow
3. **End-to-End Tests:** Test full simulation with database logging
4. **Performance Tests:** Ensure warmup doesn't slow down startup significantly

### Deployment Checklist:

- [ ] All high-priority files implemented
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Configuration files updated
- [ ] Documentation updated
- [ ] Backward compatibility verified
- [ ] Error handling comprehensive
- [ ] Logging adequate for debugging
- [ ] Performance acceptable (warmup < 10 seconds for 200 candles)

---

## SUMMARY

**Completed:** 7/20 files (35%)
- All core infrastructure (CandleAggregator, WarmupManager)
- All strategy updates (base, Supertrend, RSI Momentum)
- All indicator enhancements
- MarketSimulator integration

**Remaining:** 13/20 files (65%)
- **Critical:** main.py (orchestration)
- **Important:** dashboard_integrated.py, DataManager enhancements
- **Medium:** OrderManager, RiskManager, TrailingStopLossManager
- **Low:** Config files, templates, README, tests

**Next Steps:**
1. Implement main.py integration (CRITICAL)
2. Enhance DataManager with all logging methods
3. Update dashboard_integrated.py for warmup display
4. Update remaining core components (OrderManager, RiskManager, TrailingStopLossManager)
5. Update configuration and documentation
6. Write comprehensive tests

**Estimated Remaining Work:** 4-6 hours for complete implementation and testing
