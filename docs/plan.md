# VELOX - Multi-Strategy Trading System
## 3-Day Development Plan with Daily Validation

---

## DAY 1: DATA PIPELINE & INFRASTRUCTURE (8-10 hours)

### MORNING SESSION (4 hours)

#### Task 1.1: Environment Setup (45 mins)
**Objective:** Prepare Ubuntu development environment

**Steps:**
1. Install Python 3.10+, pip, virtualenv
2. Create project: `mkdir velox && cd velox`
3. Setup venv: `python3 -m venv venv && source venv/bin/activate`
4. Install libraries:
   ```bash
   pip install pandas numpy kafka-python pyyaml flask flask-socketio
   pip install python-socketio eventlet ta-lib
   ```
5. Install Docker: `sudo apt install docker.io docker-compose`
6. Add user to docker group: `sudo usermod -aG docker $USER` (logout/login)

**Validation:**
- `python --version` shows 3.10+
- `docker --version` works
- `pip list` shows all packages

---

#### Task 1.2: Kafka Setup (30 mins)
**Objective:** Message broker for data flow

**Steps:**
1. Create `docker-compose.yml`:
```yaml
version: '3'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    ports:
      - "2181:2181"

  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    ports:
      - "9092:9092"
```

2. Start Kafka: `docker-compose up -d`
3. Verify: `docker ps` (should show 2 containers)
4. Create topics:
```bash
docker exec -it $(docker ps -qf "name=kafka") kafka-topics \
  --create --topic market.ticks --bootstrap-server localhost:9092
docker exec -it $(docker ps -qf "name=kafka") kafka-topics \
  --create --topic signals --bootstrap-server localhost:9092
docker exec -it $(docker ps -qf "name=kafka") kafka-topics \
  --create --topic orders --bootstrap-server localhost:9092
docker exec -it $(docker ps -qf "name=kafka") kafka-topics \
  --create --topic order_fills --bootstrap-server localhost:9092
docker exec -it $(docker ps -qf "name=kafka") kafka-topics \
  --create --topic positions --bootstrap-server localhost:9092
```

**Validation:**
```bash
docker exec -it $(docker ps -qf "name=kafka") kafka-topics \
  --list --bootstrap-server localhost:9092
```
Should show all 5 topics.

---

#### Task 1.3: Logging Infrastructure (45 mins)
**Objective:** Comprehensive logging for debugging

**Steps:**
1. Create `src/utils/logging_config.py`:
   - Setup format: `[timestamp] [level] [component] [strategy_id] message`
   - Create logs/ directory
   - Configure file handler: `logs/velox_YYYYMMDD.log`
   - Configure console handler with colors
   - Create component loggers: simulator, strategy, risk, order, position

2. Log levels:
   - DEBUG: Detailed flow (every tick, indicator value)
   - INFO: Important events (signals, orders, position changes)
   - WARNING: Risk blocks, anomalies
   - ERROR: Exceptions, failures

3. Add timestamp precision: milliseconds

**Validation:**
- Create test script that logs from each component
- Check log file exists with correct format
- Verify console shows colored output

---

#### Task 1.4: Data Infrastructure (2 hours)
**Objective:** Access 15-year historical data

**Steps:**

1. **Create `src/adapters/data/base.py`** (15 mins)
   - Abstract class `DataAdapter` with methods:
     - `get_data(date, symbols)` → DataFrame
     - `get_available_dates(symbol)` → list
     - `get_date_range(start, end, symbols)` → DataFrame

2. **Create `src/adapters/data/historical.py`** (1 hour)
   - Class `HistoricalDataManager`:
     - `__init__(data_directory)`: scan directory, index all CSV files
     - `_scan_directory()`: build dict of {symbol: [available_dates]}
     - `load_date(date, symbols)`: read CSVs for specific date
     - `_validate_data(df)`: check no gaps, OHLC valid, volumes >= 0
     - `_cache_management()`: keep last 10 days in memory, free older
   - Expected CSV format: `{symbol}_1min_YYYY.csv` or `{symbol}_YYYYMMDD.csv`
   - Columns: timestamp, open, high, low, close, volume

3. **Create `src/utils/data_validator.py`** (30 mins)
   - Check each loaded day:
     - Row count ~375 (9:15-3:30 = 375 minutes)
     - No timestamp gaps
     - OHLC relationships valid
     - Flag anomalies: >5% jumps in 1 minute
   - Generate report: data_quality_report.txt

4. **Test data loading** (15 mins)
   - Load 5 random dates from different years
   - Verify all 5 symbols present
   - Log statistics: date range available, total days

**Validation:**
```python
from src.adapters.data.historical import HistoricalDataManager
hdm = HistoricalDataManager("/path/to/your/15year/csvs")
print(hdm.get_available_dates('RELIANCE'))  # Should show 3000+ dates
df = hdm.load_date('2020-09-15', ['RELIANCE', 'TCS'])
print(df.shape)  # Should be (750, 6) for 2 symbols
```

---

### AFTERNOON SESSION (4 hours)

#### Task 1.5: Market Simulator with Realistic Tick Generation (2.5 hours)
**Objective:** Replay historical data with realistic intra-minute tick simulation

**Steps:**

1. **Create `src/core/market_simulator.py`** (2 hours)
   - Class `MarketSimulator`:
     - Attributes:
       - `data_adapter`: HistoricalDataManager instance
       - `current_date`: selected date
       - `symbols`: list
       - `playback_speed`: 1.0, 10.0, 100.0, 1000.0
       - `current_time`: datetime tracking simulated time
       - `data_buffer`: loaded candle data (1-min OHLC)
       - `is_running`: bool
       - `tick_count`: counter
       - `ticks_per_candle`: 10 (simulate 10 ticks per minute)
     
     - Methods:
       - `__init__(data_adapter, date, symbols, speed=1.0, ticks_per_candle=10)`
       - `load_data()`: read date from adapter, sort by timestamp
       - `start()`: set is_running=True, begin iteration
       - `pause()`: set is_running=False
       - `resume()`: set is_running=True
       - `set_speed(multiplier)`: update playback_speed
       - `jump_to_time(target_time)`: skip to specific time
       - `get_status()`: return dict with progress, current_time, ticks_remaining
       
       - `generate_realistic_ticks(candle)` → list[dict]:
         ```
         Purpose: Generate realistic tick sequence from OHLC candle
         
         Input: {open: 2450, high: 2475, low: 2445, close: 2470, volume: 15000}
         
         Algorithm:
         1. Determine price path based on candle pattern:
            - If close > open (bullish): L → O → H → C
            - If close < open (bearish): H → O → L → C
            - If close == open (neutral): O → H → L → C
         
         2. Generate ticks_per_candle (default 10) prices along path:
            - Interpolate between key points
            - Add small random variations (±0.02%)
            - Ensure constraints: min <= all ticks <= max
         
         3. Distribute volume across ticks:
            - Higher volume near OHLC transition points
            - Random distribution with total = candle volume
         
         4. Generate bid/ask spread:
            - Spread = price * 0.0005 (0.05% typical)
            - Bid = price - spread/2
            - Ask = price + spread/2
         
         Example output for bullish candle:
         [
           {time: 09:15:00.0, price: 2445, bid: 2444.9, ask: 2445.1, vol: 1200},
           {time: 09:15:06.0, price: 2448, bid: 2447.9, ask: 2448.1, vol: 1400},
           {time: 09:15:12.0, price: 2450, bid: 2449.9, ask: 2450.1, vol: 1600},
           {time: 09:15:18.0, price: 2455, bid: 2454.9, ask: 2455.1, vol: 1800},
           {time: 09:15:24.0, price: 2460, bid: 2459.9, ask: 2460.1, vol: 1700},
           {time: 09:15:30.0, price: 2465, bid: 2464.9, ask: 2465.1, vol: 1500},
           {time: 09:15:36.0, price: 2470, bid: 2469.9, ask: 2470.1, vol: 1600},
           {time: 09:15:42.0, price: 2475, bid: 2474.9, ask: 2475.1, vol: 1900},
           {time: 09:15:48.0, price: 2472, bid: 2471.9, ask: 2472.1, vol: 1400},
           {time: 09:15:54.0, price: 2470, bid: 2469.9, ask: 2470.1, vol: 1500}
         ]
         ```
       
       - `run_simulation(callback_fn)`: main loop
         - For each candle in data_buffer:
           - Generate realistic ticks using generate_realistic_ticks()
           - For each tick:
             - Sleep based on speed
             - Call callback_fn(tick_data)
             - Update current_time
           - Log every 100 candles processed
       
       - `get_next_tick()`: internal method to fetch next generated tick

2. **Add price path logic** (30 mins)
   - Create `_determine_price_path(ohlc)`:
     - Bullish (C > O): Low → Open → High → Close
     - Bearish (C < O): High → Open → Low → Close
     - Doji (C ≈ O): Open → High → Low → Close
   - Interpolate prices between path points
   - Add realistic noise (±0.01-0.02%)

3. **Logging in simulator** (15 mins)
   - Log on initialization: "Loaded {N} candles, will generate {N*10} ticks"
   - Log every 1000 ticks: "Processed 1000 ticks, current time: 10:30:45"
   - Log completion: "Simulation complete. {N} ticks in {T} seconds"

4. **Add controls** (15 mins)
   - Signal handling: Ctrl+C pauses, not exits
   - Status query: can check progress anytime

**Validation:**
- Run simulator for Sep 15, 2020 at 100x speed
- Should generate ~18,750 ticks (5 symbols × 375 minutes × 10 ticks/min)
- Check price constraints: all ticks between low-high of candle
- Verify bid/ask spread realistic
- Volume sum matches candle volume

---

#### Task 1.6: Kafka Integration (1.5 hours)
**Objective:** Stream simulated data through Kafka

**Steps:**

1. **Create `src/utils/kafka_helper.py`** (30 mins)
   - Class `KafkaProducerWrapper`:
     - Initialize with bootstrap_servers, topic
     - JSON serializer
     - `send(message_dict)`: publish to Kafka
     - `flush()`: ensure all sent
     - `close()`: cleanup
   - Class `KafkaConsumerWrapper`:
     - Initialize with bootstrap_servers, topic, group_id
     - JSON deserializer
     - `consume()`: generator yielding messages
     - `close()`: cleanup

2. **Update simulator to publish** (30 mins)
   - Add `kafka_producer` parameter to MarketSimulator
   - In `run_simulation()`, after callback, publish tick to Kafka:
     ```python
     tick_message = {
       'timestamp': tick['timestamp'].isoformat(),
       'symbol': tick['symbol'],
       'open': float(tick['open']),
       'high': float(tick['high']),
       'low': float(tick['low']),
       'close': float(tick['close']),
       'volume': int(tick['volume']),
       'source': 'simulator'
     }
     kafka_producer.send(tick_message)
     ```

3. **Create test consumer** (30 mins)
   - Script: `tests/test_kafka_consumer.py`
   - Consumes from market.ticks topic
   - Prints first 20 messages
   - Validates format
   - Counts messages received

**Validation:**
- Terminal 1: Run `python tests/test_kafka_consumer.py`
- Terminal 2: Run simulator
- Terminal 1 should show ticks being received
- Count should match ticks sent

---

#### Task 1.7: Day 1 Integration Test (30 mins)
**Objective:** Verify complete data pipeline

**Steps:**

1. **Create `tests/day1_validation.py`**:
   - Automated checks:
     - Kafka containers running
     - Topics created
     - Data loads from 5 random dates
     - Simulator processes full day
     - Kafka receives all messages
     - Logs are structured
   
2. **Manual test script `run_day1_test.sh`**:
```bash
#!/bin/bash
echo "=== DAY 1 VALIDATION ==="
echo "1. Checking Kafka..."
docker ps | grep kafka
echo "2. Loading data..."
python -c "from src.adapters.data.historical import HistoricalDataManager; hdm=HistoricalDataManager('./data'); print(f'Available: {len(hdm.get_available_dates(\"RELIANCE\"))} dates')"
echo "3. Running simulation..."
python tests/run_simulation.py --date 2020-09-15 --speed 100
echo "4. Checking logs..."
tail -20 logs/velox_*.log
echo "=== VALIDATION COMPLETE ==="
```

**Success Criteria:**
```
✓ Kafka: 2/2 containers UP
✓ Topics: 5/5 created
✓ Data: Loaded dates from 2010, 2015, 2020, 2024
✓ Simulator: 1875 ticks in ~20 seconds at 100x
✓ Kafka: 1875 sent = 1875 received
✓ Logs: Structured entries visible
```

**STOP HERE if any validation fails. Fix before Day 2.**

---

## DAY 2: STRATEGY ENGINE & RISK MANAGEMENT (10-12 hours)

### MORNING SESSION (5 hours)

#### Task 2.1: Adapter Architecture (1.5 hours)
**Objective:** Plugin system for brokers and strategies

**Steps:**

1. **Create `src/adapters/broker/base.py`** (20 mins)
   - Abstract class `BrokerAdapter`:
     - Methods (all must be implemented):
       - `connect()` → bool
       - `disconnect()` → None
       - `place_order(symbol, action, quantity, order_type, price)` → dict
       - `get_order_status(order_id)` → dict
       - `get_positions()` → list[dict]
       - `get_account_info()` → dict (capital, margin_available)
     - Return format standardized as dicts

2. **Create `src/adapters/broker/simulated.py`** (45 mins)
   - Class `SimulatedBrokerAdapter(BrokerAdapter)`:
     - Maintains internal state: positions, orders, capital
     - `place_order()`: 
       - Market order: fill at current_price + random(0.05-0.1%)
       - Limit order: queue until price matches
       - Return order dict with order_id, status, filled_price
     - `get_positions()`: return internal positions
     - Logs every order and fill

3. **Create `src/adapters/broker/factory.py`** (15 mins)
   - Class `BrokerFactory`:
     - `create(broker_type, config)` → BrokerAdapter
     - If type=='simulated': return SimulatedBrokerAdapter
     - If type=='zerodha': return ZerodhaBrokerAdapter (stub for now)
     - Reads from config file

4. **Create `src/adapters/strategy/base.py`** (30 mins)
   - Abstract class `StrategyAdapter`:
     - Attributes: strategy_id, symbols, config, positions
     - Methods:
       - `initialize()` → None
       - `on_tick(tick_data)` → None
       - `on_candle_close(candle_data, timeframe)` → None
       - `get_signals()` → list[dict]
       - `get_positions()` → dict
       - `square_off_all()` → list[dict]

**Validation:**
```python
from src.adapters.broker.factory import BrokerFactory
broker = BrokerFactory.create('simulated', {})
broker.connect()
order = broker.place_order('RELIANCE', 'BUY', 10, 'MARKET', None)
print(order)  # Should show order_id, filled_price
```

---

#### Task 2.2: Technical Indicators (1 hour)
**Objective:** Real-time indicator calculation

**Steps:**

1. **Create `src/utils/indicators.py`** (45 mins)
   - Class `TechnicalIndicators`:
     - Attributes:
       - `symbol`: str
       - `price_history`: list (keep last 100 prices)
       - `high_history`, `low_history`: for ATR
     - Methods:
       - `add_price(close, high, low)`: append to history
       - `calculate_rsi(period=14)` → float:
         - Delta calculation
         - Average gain/loss
         - RS = avg_gain / avg_loss
         - RSI = 100 - (100 / (1 + RS))
         - Assert 0 <= RSI <= 100
       - `calculate_ma(period=20)` → float:
         - Simple moving average
       - `calculate_atr(period=14)` → float:
         - True Range = max(H-L, |H-PC|, |L-PC|)
         - ATR = average of last N true ranges
       - `get_all()` → dict with all indicators
   - Validate calculations against known test data

2. **Create `src/core/indicator_manager.py`** (15 mins)
   - Class `IndicatorManager`:
     - Maintains dict of {symbol: TechnicalIndicators}
     - `process_tick(tick_data)`: update relevant symbol's indicators
     - `get_indicators(symbol)` → dict

**Validation:**
```python
from src.utils.indicators import TechnicalIndicators
ti = TechnicalIndicators('TEST')
for price in [50, 51, 52, 48, 47, 49, 51, 53, 52, 51]:
    ti.add_price(price, price, price)
rsi = ti.calculate_rsi(period=5)
print(f"RSI: {rsi}")  # Should be around 45-55
```

---

#### Task 2.3: First Strategy Implementation (2.5 hours)
**Objective:** RSI + MA momentum strategy

**Steps:**

1. **Create `src/adapters/strategy/rsi_momentum.py`** (2 hours)
   - Class `RSIMomentumStrategy(StrategyAdapter)`:
     - Attributes:
       - `strategy_id`: from config
       - `symbols`: list
       - `indicator_manager`: IndicatorManager instance
       - `open_positions`: dict
       - Config params:
         - `rsi_period`: 14
         - `rsi_oversold`: 30
         - `rsi_overbought`: 70
         - `ma_period`: 20
         - `target_pct`: 0.02
         - `initial_sl_pct`: 0.01
     
     - `on_tick(tick_data)`:
       - Update indicators
       - If symbol in positions: check_exit_conditions()
       - Else: check_entry_conditions()
     
     - `check_entry_conditions(symbol, tick_data)`:
       - Get indicators
       - **Log detailed check:**
         ```
         [SIGNAL_CHECK] [strategy_id] Symbol: RELIANCE @ 2450.50
         ├─ RSI: 28.5 < 30 (oversold threshold) → PASS ✓
         ├─ MA(20): 2445.30
         ├─ Price > MA: 2450.50 > 2445.30 → PASS ✓
         ├─ Volume check: 1500 > 500 → PASS ✓
         └─ DECISION: GENERATE BUY SIGNAL
         ```
       - If all conditions met:
         - Create signal dict:
           ```python
           signal = {
             'strategy_id': self.strategy_id,
             'action': 'BUY',
             'symbol': symbol,
             'price': current_price,
             'timestamp': tick_data['timestamp'],
             'reason': f"RSI={rsi:.2f} < {self.rsi_oversold} AND Price > MA",
             'indicators': {...}
           }
           ```
         - Publish to Kafka signals topic
         - Return signal
     
     - `check_exit_conditions(symbol, tick_data)`:
       - Calculate P&L percentage
       - **Log exit check:**
         ```
         [EXIT_CHECK] [strategy_id] Position: RELIANCE
         ├─ Entry: 2450.00, Current: 2475.50
         ├─ P&L: +1.04% (target: 2%, current unrealized)
         ├─ RSI: 68.5 (overbought: 70)
         ├─ Stop-loss: 2425.50 (current > SL)
         └─ DECISION: HOLD (no exit condition met)
         ```
       - Exit if:
         - P&L >= target_pct: "Target hit"
         - P&L <= -initial_sl_pct: "Stop-loss hit"
         - RSI > rsi_overbought: "RSI overbought"
       - Create SELL signal if exit triggered

2. **Create `src/adapters/strategy/registry.py`** (30 mins)
   - Class `StrategyRegistry`:
     - Static dict: `_strategies = {}`
     - `register(name, strategy_class)`: add to dict
     - `get(name, config)`: instantiate and return strategy
     - `list_available()`: return registered strategy names

**Validation:**
- Create test that feeds known tick data
- Verify RSI calculation correct
- Check signal generated when conditions met
- Verify logs show decision breakdown

---

### AFTERNOON SESSION (5 hours)

#### Task 2.4: Multi-Strategy Manager (2 hours)
**Objective:** Orchestrate multiple concurrent strategies

**Steps:**

1. **Create `src/core/strategy_manager.py`** (1.5 hours)
   - Class `StrategyManager`:
     - Attributes:
       - `strategies`: list[StrategyAdapter]
       - `kafka_consumer`: consume from market.ticks
       - `kafka_producer`: publish to signals
     
     - `__init__(config_file)`:
       - Load config/strategies.yaml
       - For each enabled strategy:
         - Get class from registry
         - Instantiate with config
         - Add to strategies list
       - Log: "Loaded {N} strategies: {names}"
     
     - `start()`:
       - Infinite loop consuming market.ticks
       - For each tick:
         - Distribute to all strategies: `strategy.on_tick(tick)`
       - Each strategy independently:
         - Updates indicators
         - Checks conditions
         - Generates signals
         - Publishes to Kafka with strategy_id tag
     
     - `stop()`:
       - Call square_off_all() on each strategy
       - Close Kafka connections

2. **Create config file `config/strategies.yaml`** (30 mins)
   ```yaml
   strategies:
     - id: rsi_aggressive
       class: RSIMomentumStrategy
       enabled: true
       symbols: [RELIANCE, TCS]
       params:
         rsi_oversold: 30
         rsi_overbought: 70
         ma_period: 20
         target_pct: 0.03
         initial_sl_pct: 0.015
       trailing_sl:
         type: fixed_pct
         trigger_pct: 0.01
         trail_pct: 0.005
     
     - id: rsi_conservative
       class: RSIMomentumStrategy
       enabled: true
       symbols: [INFY, HDFC]
       params:
         rsi_oversold: 25
         rsi_overbought: 70
         ma_period: 50
         target_pct: 0.02
         initial_sl_pct: 0.01
       trailing_sl:
         type: atr
         multiplier: 2.0
         period: 14
   ```

**Validation:**
- Load 2 strategies from config
- Feed same tick data to both
- Verify each generates independent signals
- Check strategy_id tagged correctly

---

#### Task 2.5: Trailing Stop-Loss Engine (2 hours)
**Objective:** Dynamic SL per strategy

**Steps:**

1. **Create `src/core/trailing_sl_manager.py`** (1.5 hours)
   - Class `TrailingSLManager`:
     - Attributes:
       - `strategy_id`: str
       - `sl_config`: dict from strategy config
       - `sl_type`: 'fixed_pct' | 'atr' | 'ma' | 'time_decay'
       - `positions`: dict[symbol, PositionSL]
     
     - Inner class `PositionSL`:
       - `entry_price`: float
       - `highest_price`: float (tracks peak)
       - `current_sl`: float
       - `trigger_activated`: bool
       - `entry_time`: datetime
     
     - Methods:
       - `add_position(symbol, entry_price)`:
         - Create PositionSL
         - Set initial SL = entry_price * (1 - initial_sl_pct)
       
       - `update(symbol, current_price, indicators)`:
         - Update highest_price if new high
         - Calculate new SL based on type:
           
           **Fixed %:**
           - If (highest - entry) / entry >= trigger_pct:
             - Activate trail
             - new_sl = highest * (1 - trail_pct)
           
           **ATR:**
           - new_sl = highest - (ATR * multiplier)
           
           **MA:**
           - new_sl = current_ma_value
           
           **Time Decay:**
           - elapsed = now - entry_time
           - progress = elapsed / duration
           - sl_pct = initial + (final - initial) * progress
           - new_sl = entry * (1 - sl_pct)
         
         - If new_sl > current_sl:
           - Update current_sl (only moves up)
           - Log: `[TRAIL_SL] [strategy_id] Symbol: SL 2460 → 2465 (+0.2%)`
       
       - `check_trigger(symbol, current_price)` → bool:
         - Return current_price <= current_sl
       
       - `remove_position(symbol)`:
         - Delete from positions dict

2. **Integrate with strategy** (30 mins)
   - Add `trailing_sl_manager` to each strategy instance
   - In `check_exit_conditions()`:
     - Update trailing SL
     - Check if triggered
     - If yes: generate SELL signal with reason "Trailing SL hit"

**Validation:**
- Simulate position: entry 2450
- Feed prices: 2450 → 2460 → 2475 → 2470 → 2465
- For fixed_pct (trigger 1%, trail 0.5%):
  - At 2475: trigger activated (>1%), SL = 2475*0.995 = 2462.6
  - At 2470: SL stays 2462.6
  - At 2465: SL triggered, exit signal

---

#### Task 2.6: Risk Manager (1 hour)
**Objective:** Multi-strategy risk control

**Steps:**

1. **Create `src/core/risk_manager.py`** (45 mins)
   - Class `RiskManager`:
     - Attributes:
       - `capital`: float
       - `global_max_positions`: int (10)
       - `global_max_daily_loss_pct`: float (0.03)
       - `strategy_limits`: dict (per-strategy from config)
       - `current_positions`: dict[tuple(strategy_id, symbol), Position]
       - `daily_pnl`: float
       - `trades_today`: int
     
     - `validate_signal(signal)` → tuple[bool, str]:
       - strategy_id = signal['strategy_id']
       - action = signal['action']
       
       - **Log detailed check:**
         ```
         [RISK_CHECK] [strategy_id] BUY RELIANCE @ 2450
         ├─ Strategy positions: 2/3 → PASS ✓
         ├─ Global positions: 7/10 → PASS ✓
         ├─ Daily P&L: -₹1,200 / -₹3,000 limit → PASS ✓
         ├─ Capital available: 75% → PASS ✓
         ├─ Symbol conflict: No existing position → PASS ✓
         └─ DECISION: APPROVED
         ```
       
       - BUY checks:
         - Strategy position count < strategy_limit
         - Global position count < global_limit
         - Daily P&L > -global_max_daily_loss
         - No existing position in (strategy_id, symbol)
       
       - SELL checks:
         - Position exists for (strategy_id, symbol)
       
       - Return (True, reason) or (False, reason)
     
     - `add_position(strategy_id, symbol, entry_price, quantity)`
     - `close_position(strategy_id, symbol, exit_price)`:
       - Calculate P&L
       - Update daily_pnl
       - Log with details

2. **Create `src/core/signal_processor.py`** (15 mins)
   - Consumes from signals topic
   - For each signal:
     - Call risk_manager.validate_signal()
     - If approved: publish to orders topic
     - If rejected: log rejection

**Validation:**
- Create 3 positions in one strategy
- Send 4th signal: should be rejected (strategy limit)
- Create 7 global positions
- Send signal from different strategy: test global limit

---

#### Task 2.7: Order & Position Management (1 hour)
**Objective:** Execution and tracking

**Steps:**

1. **Create `src/core/order_manager.py`** (30 mins)
   - Class `OrderManager`:
     - Attributes:
       - `broker`: BrokerAdapter
       - `kafka_consumer`: consume from orders
       - `kafka_producer`: publish to order_fills
       - `pending_orders`: dict
     
     - `start()`:
       - Consume orders topic
       - For each order:
         - Call broker.place_order()
         - Store in pending_orders
         - Log order sent
         - When filled:
           - Publish to order_fills topic
           - Log execution details
           - Remove from pending

2. **Create `src/core/position_tracker.py`** (30 mins)
   - Class `PositionTracker`:
     - Consumes from order_fills
     - Updates risk_manager positions
     - Updates strategy positions
     - Publishes to positions topic
     - Logs every position change

**Validation:**
- Send order → verify broker receives
- Check fill published to Kafka
- Verify position tracker updates

---

#### Task 2.8: Day 2 Integration Test (30 mins)
**Objective:** End-to-end signal flow

**Steps:**

1. **Create `tests/day2_validation.py`**:
   - Start all components
   - Feed Sep 15, 2020 data at 10x speed
   - Expected flow:
     - Tick → Indicators → Strategy → Signal → Risk → Order → Fill → Position
   - Verify:
     - Signals generated (expected 5-10)
     - Risk blocks when limits hit
     - Trailing SL updates
     - Positions tracked correctly

2. **Manual checks:**
   - Check logs for complete decision trail
   - Verify each signal has condition breakdown
   - Confirm risk checks logged
   - Check trailing SL logs show updates

**Success Criteria:**
```
✓ Indicators: RSI calculated correctly
✓ Signals: 2 strategies generated 7 total signals
✓ Strategy isolation: independent positions
✓ Trailing SL: updated 5 times, triggered once
✓ Risk manager: blocked 1 signal (max positions)
✓ Position tracking: matches order fills
```

**STOP HERE if signal logic unclear or SL not working. Debug using logs.**

---

## DAY 3: DASHBOARD, TESTING & VALIDATION (8-10 hours)

### MORNING SESSION (4 hours)

#### Task 3.1: Web Dashboard (3 hours)
**Objective:** Real-time monitoring interface

**Steps:**

1. **Create `src/dashboard/app.py`** (1.5 hours)
   - Flask app with SocketIO
   - Endpoints:
     - `GET /` → serve index.html
     - `GET /api/status` → system health JSON
     - `GET /api/strategies` → per-strategy metrics
     - `GET /api/positions` → all open positions
     - `WS /logs` → stream logs in real-time
   
   - Background tasks:
     - Consume from Kafka positions topic
     - Consume from Kafka signals topic
     - Tail log file
     - Emit updates via WebSocket every 1 second

2. **Create `src/dashboard/templates/index.html`** (1.5 hours)
   - Single page application
   - Layout:
   
   **Panel 1: Strategy Status Table**
   ```
   | Strategy ID      | Status | Positions | Signals Today | P&L      | Win Rate |
   |------------------|--------|-----------|---------------|----------|----------|
   | rsi_aggressive   | Active | 2/3       | 5             | +₹850    | 60%      |
   | rsi_conservative | Active | 1/2       | 3             | +₹1,200  | 100%     |
   ```
   
   **Panel 2: Open Positions by Strategy**
   ```
   | Strategy     | Symbol   | Entry  | Current | SL Type  | Current SL | P&L   |
   |--------------|----------|--------|---------|----------|------------|-------|
   | rsi_agg      | RELIANCE | 2450   | 2475    | Fixed %  | 2462 (↑)   | +1.0% |
   | rsi_cons     | TCS      | 3200   | 3220    | ATR      | 3195 (↑)   | +0.6% |
   ```
   
   **Panel 3: Live Log Stream**
   - Last 100 log lines
   - Auto-scroll
   - Color-coded by level (ERROR=red, WARNING=yellow, INFO=white, DEBUG=gray)
   - Filters:
     - By component: All | Strategy | Risk | Orders | Position
     - By strategy: All | rsi_aggressive | rsi_conservative
     - By log level: All | ERROR | WARNING | INFO | DEBUG
   - Search box for symbol filtering
   
   **Panel 4: Trailing SL Activity Feed**
   ```
   [14:30:15] [rsi_agg] RELIANCE: Price 2475, SL 2460 → 2462 (+0.08%)
   [14:28:30] [rsi_agg] RELIANCE: Trail activated at +1.2% profit
   [14:25:10] [rsi_cons] TCS: ATR SL updated 3190 → 3195 (ATR=25.3)
   ```
   
   **Panel 5: System Status**
   ```
   Kafka:           ● Connected (lag: 12ms)
   Last Tick:       2s ago (RELIANCE @ 2475.50)
   Strategies:      2/2 active
   Total Positions: 3/10
   Daily P&L:       +₹2,050 (+2.05%)
   ```
   
   - JavaScript:
     - Socket.IO client connecting to backend
     - Auto-refresh every 1 second
     - Chart.js for P&L curve (optional)
     - Update DOM elements with new data

**Validation:**
- Start dashboard: `python src/dashboard/app.py`
- Open browser: `http://localhost:5000`
- Run simulation in background
- Verify:
  - Strategy table updates
  - Positions show live prices
  - Log stream scrolls
  - SL activity appears

---

#### Task 3.2: Time-Based Controller (1 hour)
**Objective:** Auto square-off at 3:15 PM

**Steps:**

1. **Create `src/core/time_controller.py`** (45 mins)
   - Class `TimeController`:
     - Attributes:
       - `strategy_manager`: reference
       - `simulated_time`: current simulation time
       - `square_off_time`: "15:15:00"
       - `warning_time`: "15:00:00"
     
     - `check_time(current_time)`:
       - Update simulated_time
       - If current_time >= warning_time:
         - Log: "WARNING: 15 minutes to square-off"
         - Set flag to stop new entries
       - If current_time >= square_off_time:
         - Call strategy_manager.square_off_all()
         - Log each position closed
         - Verify position count = 0
         - Generate EOD summary
     
     - `square_off_all()`:
       - For each strategy:
         - Get open positions
         - Generate SELL signals with priority flag
         - Force close at market price
       - Log: "EOD Square-off complete. {N} positions closed. Total P&L: ₹{amount}"

2. **Integrate with simulator** (15 mins)
   - In MarketSimulator.run_simulation():
     - After each tick, call time_controller.check_time(tick_timestamp)

**Validation:**
- Run simulation from 3:00 PM to 3:30 PM
- At 3:00: warning logged
- At 3:15: all positions closed
- Final position count = 0

---

### AFTERNOON SESSION (5 hours)

#### Task 3.3: Configuration Management (1 hour)
**Objective:** Centralized config system

**Steps:**

1. **Create `config/system.yaml`** (20 mins)
```yaml
system:
  broker:
    type: simulated  # simulated | zerodha | upstox
    capital: 100000
  
  risk:
    global_max_positions: 10
    global_daily_loss_pct: 0.03
  
  kafka:
    bootstrap_servers: localhost:9092
    consumer_group: velox-consumer
  
  logging:
    level: INFO  # DEBUG | INFO | WARNING | ERROR
    file_retention_days: 30
```

2. **Create `config/symbols.yaml`** (10 mins)
```yaml
watchlist:
  - RELIANCE
  - TCS
  - INFY
  - HDFCBANK
  - ICICIBANK

# Optional: symbol-specific config
symbol_config:
  RELIANCE:
    min_volume: 100000
    max_spread_pct: 0.001
```

3. **Create `src/utils/config_loader.py`** (30 mins)
   - Class `ConfigLoader`:
     - `load_system_config()` → dict
     - `load_strategies_config()` → dict
     - `load_symbols_config()` → list
     - `validate_config()`: check required fields
     - `reload()`: hot-reload without restart

**Validation:**
- Load all configs
- Change strategy params in YAML
- Verify system uses new values

---

#### Task 3.4: Testing Framework (2 hours)
**Objective:** Automated validation suite

**Steps:**

1. **Create `tests/test_indicators.py`** (20 mins)
   - Unit tests for RSI, MA, ATR calculations
   - Test against known input/output pairs
   - Assert values within tolerance (±0.5%)

2. **Create `tests/test_strategy_logic.py`** (30 mins)
   - Test entry conditions with mock data:
     - RSI=28, Price>MA → should generate BUY
     - RSI=32, Price>MA → should NOT generate BUY
     - RSI=28, Price<MA → should NOT generate BUY
   - Test exit conditions:
     - P&L=+2.5% → should exit (target hit)
     - P&L=-1.5% → should exit (SL hit)
     - RSI=72 → should exit (overbought)

3. **Create `tests/test_trailing_sl.py`** (30 mins)
   - Test fixed_pct type:
     - Entry 2450, trigger 1%, trail 0.5%
     - Prices: 2450 → 2475 → 2470 → 2465
     - Expected: activate at 2475, SL=2462.6, trigger at 2465
   - Test ATR type with known ATR values
   - Test time_decay type

4. **Create `tests/known_scenario_test.py`** (40 mins)
   - Pick date: Sep 15, 2020
   - Manual analysis:
     - RELIANCE: RSI went below 30 at 10:30, should BUY
     - TCS: Hit target at 14:20, should SELL
   - Run strategy on this date
   - Compare actual vs expected signals
   - Store as regression baseline

**Validation:**
```bash
pytest tests/ -v
```
All tests should pass.

---

#### Task 3.5: Backtesting Engine (2 hours)
**Objective:** Historical performance analysis

**Steps:**

1. **Create `src/backtest/backtest_engine.py`** (1 hour)
   - Class `BacktestEngine`:
     - Attributes:
       - `data_manager`: HistoricalDataManager
       - `strategy_manager`: StrategyManager
       - `date_range`: start, end dates
       - `results`: dict to store metrics
     
     - `run(start_date, end_date, speed=1000.0)`:
       - For each trading day in range:
         - Load data
         - Run simulation at high speed
         - Collect results
       - Aggregate metrics
     
     - `collect_daily_metrics()`:
       - Signals generated
       - Trades executed
       - Win/loss count
       - P&L
       - Max drawdown
     
     - `generate_report()`:
       - Per-strategy breakdown
       - Equity curve
       - Trade distribution
       - Win rate, profit factor
       - Sharpe ratio (if enough data)

2. **Create `src/backtest/report_generator.py`** (1 hour)
   - HTML report with:
     - Summary table (trades, win%, P&L, drawdown)
     - Equity curve chart (cumulative P&L over time)
     - Per-strategy comparison table
     - Best/worst trading days
     - Trade list CSV download
   - Save as `reports/backtest_YYYYMMDD_HHMMSS.html`

**Validation:**
- Run backtest on Sep 2020 (22 days)
- Should complete in < 30 minutes at 1000x speed
- Report generated with all metrics
- Visual check: equity curve shows growth/decline

---

#### Task 3.6: Day 3 Integration & Final Testing (1 hour)
**Objective:** Complete system validation

**Steps:**

1. **Create `tests/day3_validation.py`** (30 mins)
   - Automated checks:
     - Dashboard responds (HTTP 200)
     - WebSocket connects
     - 3 strategies load from config
     - Square-off triggers at 3:15 PM
     - Config reload works
     - Backtest completes
     - Replay consistency (same day twice = same results)

2. **Create master test script `tests/run_all_validations.py`** (30 mins)
   - Runs all Day 1, 2, 3 validations
   - Generates comprehensive report
   - Exit code 0 if all pass, 1 if any fail

**Final Integration Test:**
```bash
# Run complete system
python src/main.py \
  --config config/system.yaml \
  --strategies config/strategies.yaml \
  --date 2020-09-15 \
  --speed 10

# Expected:
# - 3 strategies active
# - 15-25 signals generated
# - Dashboard updates in real-time
# - Positions tracked correctly
# - Square-off at 15:15
# - Final EOD summary logged
```

**Success Criteria:**
```
✓ Dashboard: Accessible at localhost:5000
✓ Multi-strategy: 3 strategies running independently
✓ Trailing SL: Updates visible in dashboard
✓ Square-off: All positions closed at 15:15
✓ Config: Changed RSI 30→25, system reloaded
✓ Backtest: 22 days in 18 mins, report generated
✓ Replay: Same date = same results (deterministic)
✓ Logs: Complete audit trail for every decision
```

---

## FINAL DELIVERABLES

### Directory Structure
```
velox/
├── config/
│   ├── system.yaml
│   ├── strategies.yaml
│   └── symbols.yaml
├── data/
│   └── historical/          # Your 15-year CSVs
├── logs/
│   └── velox_20250101.log
├── reports/
│   └── backtest_*.html
├── src/
│   ├── adapters/
│   │   ├── broker/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── simulated.py
│   │   │   ├── zerodha.py (stub)
│   │   │   └── factory.py
│   │   ├── strategy/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── rsi_momentum.py
│   │   │   └── registry.py
│   │   └── data/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       └── historical.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── market_simulator.py
│   │   ├── strategy_manager.py
│   │   ├── trailing_sl_manager.py
│   │   ├── risk_manager.py
│   │   ├── order_manager.py
│   │   ├── position_tracker.py
│   │   └── time_controller.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── indicators.py
│   │   ├── logging_config.py
│   │   ├── kafka_helper.py
│   │   └── config_loader.py
│   ├── dashboard/
│   │   ├── app.py
│   │   └── templates/
│   │       └── index.html
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── backtest_engine.py
│   │   └── report_generator.py
│   └── main.py
├── tests/
│   ├── day1_validation.py
│   ├── day2_validation.py
│   ├── day3_validation.py
│   ├── test_indicators.py
│   ├── test_strategy_logic.py
│   ├── test_trailing_sl.py
│   ├── known_scenario_test.py
│   └── run_all_validations.py
├── docker-compose.yml
├── requirements.txt
├── README.md
└── .gitignore
```

### Key Features Delivered

1. **Multi-Strategy Execution**
   - Run 3+ strategies concurrently
   - Independent position tracking
   - Per-strategy configuration

2. **Advanced Trailing Stop-Loss**
   - 4 types: fixed_pct, ATR, MA, time_decay
   - Per-strategy configuration
   - Real-time updates logged

3. **Broker Abstraction**
   - Simulated broker for testing
   - Easy to add real brokers (Zerodha, Upstox)
   - Switch via config only

4. **15-Year Historical Data**
   - Load any date from 2010-2024
   - Test across market cycles
   - Bull markets, crashes, recovery periods

5. **Real-Time Dashboard**
   - Per-strategy metrics
   - Live position tracking
   - Trailing SL visibility
   - Log streaming

6. **Comprehensive Logging**
   - Every decision logged with reasoning
   - Complete audit trail
   - Easy debugging

7. **Backtesting Framework**
   - Test on months/years of data
   - Performance comparison
   - HTML reports

8. **Config-Driven**
   - No code changes to modify strategies
   - Hot-reload capability
   - Version control friendly

---

## Quick Start Commands

```bash
# Day 1 - Test data pipeline
docker-compose up -d
python tests/day1_validation.py

# Day 2 - Test strategies
python tests/day2_validation.py

# Day 3 - Full system
python src/main.py --date 2020-09-15 --speed 10
python tests/day3_validation.py

# Run backtest
python src/backtest/backtest_engine.py \
  --start 2020-09-01 --end 2020-09-30 \
  --strategies config/strategies.yaml

# Start dashboard
python src/dashboard/app.py &
# Open: http://localhost:5000
```

---

## Daily Validation Summary

**End of Day 1:** ✓ Data flows from CSV → Kafka → Consumer
**End of Day 2:** ✓ Strategies generate signals with full reasoning
**End of Day 3:** ✓ Complete system with dashboard and backtesting

**Total Development Time:** 26-32 hours over 3 days

**Result:** Production-ready multi-strategy trading system for NSE with 15-year backtesting capability.