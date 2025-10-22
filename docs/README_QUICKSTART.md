# VELOX Trading System - Quick Start Guide

## 🚀 Quick Start (3 Steps)

### 1. Make scripts executable
```bash
chmod +x start_velox.sh stop_velox.sh run_all_tests.sh
```

### 2. Start VELOX
```bash
./start_velox.sh
```

### 3. Open Dashboard
Open your browser: **http://localhost:5000**

---

## 📋 Usage

### Start with default settings
```bash
./start_velox.sh
```
- Date: 2020-09-15
- Speed: 50x
- Dashboard: http://localhost:5000

### Start with custom date
```bash
./start_velox.sh --date 2020-09-16
```

### Start with custom port
```bash
./start_velox.sh --date 2020-09-15 --port 5001
```

### Start with tests first
```bash
./start_velox.sh --test
```

### Stop VELOX
```bash
./stop_velox.sh
```

---

## 🧪 Testing

### Run all tests
```bash
./run_all_tests.sh
```

### Run individual tests
```bash
python3 test_influx_redis.py    # Redis + InfluxDB
python3 test_sqlite.py          # SQLite
python3 test_logging.py         # Logging
python3 test_data_manager.py    # DataManager
python3 test_integration.py     # Integration
```

---

## 🐳 Docker Services

### Start services
```bash
docker compose up -d redis influxdb
```

### Stop services
```bash
docker compose stop redis influxdb
```

### Check status
```bash
docker ps | grep velox
```

### View logs
```bash
docker logs velox-redis
docker logs velox-influxdb
```

---

## 📊 Dashboard Features

- **Real-time trading simulation**
- **Strategy monitoring** (Scalping MTF ATR)
- **Position tracking**
- **P&L visualization**
- **Trade history**
- **Performance metrics**

---

## 🔧 Troubleshooting

### Port already in use
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Or use different port
python3 dashboard_final.py --port 5001
```

### Docker services not starting
```bash
# Check Docker status
docker ps

# Restart services
docker compose restart redis influxdb

# View logs
docker compose logs redis influxdb
```

### Missing Python dependencies
```bash
pip install redis influxdb-client colorlog pandas numpy
```

---

## 📁 Project Structure

```
VELOX/
├── start_velox.sh           # Start script
├── stop_velox.sh            # Stop script
├── run_all_tests.sh         # Test runner
├── dashboard_final.py       # Main dashboard
├── docker-compose.yml       # Docker services
│
├── src/
│   ├── database/            # Data layer
│   │   ├── redis_manager.py
│   │   ├── influx_manager.py
│   │   ├── sqlite_manager.py
│   │   └── data_manager.py
│   │
│   ├── adapters/
│   │   └── strategy/        # Trading strategies
│   │       ├── scalping_mtf_atr.py
│   │       └── rsi_momentum.py
│   │
│   └── utils/
│       ├── indicators.py
│       └── logging_system.py
│
├── config/
│   └── strategies.yaml      # Strategy configuration
│
├── data/                    # SQLite database
├── logs/                    # Log files
└── tests/                   # Test files
```

---

## 🎯 Available Strategies

### Scalping MTF ATR (Active)
- Multi-timeframe trend alignment
- EMA 9/21 on 5-min, EMA 50 on 15-min, EMA 200 on 1-hour
- MACD + RSI confirmation
- ATR-based stop loss (2.5x)
- Multiple take profit levels (2 ATR, 3 ATR)
- Breakeven at 1 ATR profit
- Trailing stop at 1.5 ATR profit
- Both LONG and SHORT positions

### Configuration
Edit `config/strategies.yaml` to:
- Enable/disable strategies
- Adjust parameters
- Add symbols
- Modify risk settings

---

## 📈 Performance

- **Tick Processing**: 605 ticks/sec
- **Indicator Caching**: 360 ops/sec
- **Logging**: 5,076 msgs/sec
- **Redis Access**: < 1ms
- **InfluxDB Write**: 100K+ pts/sec
- **SQLite Query**: < 10ms

---

## 🔗 Useful Commands

```bash
# Check if services are running
nc -z localhost 6379  # Redis
nc -z localhost 8086  # InfluxDB
nc -z localhost 5000  # Dashboard

# View real-time logs
tail -f logs/strategy.log
tail -f logs/database.log

# Check database size
ls -lh data/velox_trades.db

# Monitor Docker resources
docker stats velox-redis velox-influxdb
```

---

## 📚 Documentation

- **Day 4 Summary**: `DAY4_FINAL_SUMMARY.md`
- **Scalping Strategy**: `SCALPING_STRATEGY_GUIDE.md`
- **Progress**: `DAY4_PROGRESS.md`

---

## 🆘 Support

If you encounter issues:

1. Check logs: `logs/` directory
2. Run tests: `./run_all_tests.sh`
3. Verify Docker: `docker ps`
4. Check ports: `lsof -i :5000,6379,8086`

---

## ✅ System Requirements

- Python 3.8+
- Docker & Docker Compose
- 2GB RAM minimum
- Linux/macOS (Windows WSL2)

---

**Happy Trading! 🚀**
