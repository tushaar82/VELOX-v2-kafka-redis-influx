# VELOX Scripts Guide

## 🚀 Available Scripts

### 1. **start_velox.sh** - Start the system
```bash
./start_velox.sh                           # Start with defaults
./start_velox.sh --date 2020-09-16        # Custom date
./start_velox.sh --speed 100              # Custom speed
./start_velox.sh --test                   # Run tests first
./start_velox.sh --date 2020-09-15 --speed 50  # Combined
```

**What it does:**
- ✅ Checks Docker installation
- ✅ Starts Redis & InfluxDB containers
- ✅ Verifies Python dependencies
- ✅ Optionally runs tests
- ✅ Starts dashboard on http://localhost:5000

---

### 2. **stop_velox.sh** - Stop the system
```bash
./stop_velox.sh
```

**What it does:**
- ✅ Stops dashboard
- ✅ Stops Docker containers (Redis, InfluxDB)
- ✅ Clean shutdown

---

### 3. **status_velox.sh** - Check system status
```bash
./status_velox.sh
```

**What it shows:**
- ✅ Redis status (port 6379)
- ✅ InfluxDB status (port 8086)
- ✅ Dashboard status (port 5000)
- ✅ SQLite database size
- ✅ Docker containers
- ✅ Log files

---

### 4. **run_all_tests.sh** - Run all tests
```bash
./run_all_tests.sh
```

**What it tests:**
- ✅ Redis + InfluxDB integration
- ✅ SQLite manager
- ✅ Structured logging
- ✅ Unified DataManager
- ✅ Complete integration workflow

---

## 📋 Quick Start

### First Time Setup
```bash
# 1. Make scripts executable
chmod +x *.sh

# 2. Run tests to verify everything works
./run_all_tests.sh

# 3. Start VELOX
./start_velox.sh

# 4. Open browser
# http://localhost:5000
```

### Daily Usage
```bash
# Morning: Start system
./start_velox.sh --date 2020-09-15

# Check status anytime
./status_velox.sh

# Evening: Stop system
./stop_velox.sh
```

---

## 🔧 Troubleshooting

### Script won't run
```bash
# Make executable
chmod +x start_velox.sh stop_velox.sh status_velox.sh run_all_tests.sh
```

### Port already in use
```bash
# Check what's using port 5000
lsof -i :5000

# Kill it
lsof -ti:5000 | xargs kill -9

# Or stop everything
./stop_velox.sh
```

### Docker services not starting
```bash
# Check Docker
docker ps

# Restart services
docker compose restart redis influxdb

# View logs
docker logs velox-redis
docker logs velox-influxdb
```

### Tests failing
```bash
# Check if services are running
./status_velox.sh

# Start services
docker compose up -d redis influxdb

# Wait 5 seconds, then test
sleep 5 && ./run_all_tests.sh
```

---

## 📊 System Status Output

```
====================================================================
📊 VELOX TRADING SYSTEM - STATUS
====================================================================

🔴 Redis:
✅ Running on port 6379
   Responding to commands

📊 InfluxDB:
✅ Running on port 8086
   Health check passed

🎯 Dashboard:
✅ Running on port 5000
   URL: http://localhost:5000

💾 SQLite:
✅ Database exists (44K)

🐳 Docker Containers:
NAMES            STATUS                    PORTS
velox-influxdb   Up 23 minutes (healthy)   0.0.0.0:8086->8086/tcp
velox-redis      Up 24 minutes (healthy)   0.0.0.0:6379->6379/tcp

📝 Recent Logs:
✅ Log directory exists
   logs/strategy.log (300)
   logs/database.log (162)
   ...
====================================================================
```

---

## 🎯 Script Options

### start_velox.sh Options

| Option | Description | Example |
|--------|-------------|---------|
| `--date YYYY-MM-DD` | Set simulation date | `--date 2020-09-16` |
| `--speed N` | Set simulation speed | `--speed 100` |
| `--test` | Run tests before starting | `--test` |

### Default Values
- **Date**: 2020-09-15
- **Speed**: 50x
- **Port**: 5000

---

## 📁 Files Created by Scripts

```
VELOX/
├── data/
│   └── velox_trades.db          # SQLite database
│
├── logs/
│   ├── strategy.log             # Strategy logs
│   ├── strategy_json.log        # JSON format
│   ├── database.log             # Database logs
│   └── ...                      # Other component logs
│
└── Docker volumes:
    ├── redis-data/              # Redis persistence
    ├── influxdb-data/           # InfluxDB data
    └── influxdb-config/         # InfluxDB config
```

---

## 🔗 Related Commands

### Docker Management
```bash
# View all containers
docker ps -a

# View logs
docker logs -f velox-redis
docker logs -f velox-influxdb

# Restart a service
docker restart velox-redis

# Remove containers (keeps data)
docker compose down

# Remove containers and data
docker compose down -v
```

### Log Management
```bash
# View real-time logs
tail -f logs/strategy.log

# View JSON logs
tail -f logs/strategy_json.log | jq

# Clear old logs
rm logs/*.log
```

### Database Management
```bash
# Check SQLite database
sqlite3 data/velox_trades.db "SELECT COUNT(*) FROM trades;"

# Backup database
cp data/velox_trades.db data/velox_trades_backup.db

# Check Redis
docker exec velox-redis redis-cli INFO

# Check InfluxDB
curl http://localhost:8086/health
```

---

## ⚡ Performance Tips

1. **Increase Speed**: Use `--speed 100` for faster simulation
2. **Reduce Logging**: Edit `src/utils/logging_system.py` to change log level
3. **Monitor Resources**: Use `docker stats` to check memory/CPU usage
4. **Clean Logs**: Periodically delete old log files

---

## 🆘 Emergency Commands

```bash
# Kill everything
pkill -f dashboard_final
docker compose down
killall python3

# Fresh start
./stop_velox.sh
docker compose down -v
docker compose up -d redis influxdb
./start_velox.sh
```

---

## ✅ Checklist Before Running

- [ ] Docker installed and running
- [ ] Python 3.8+ installed
- [ ] Scripts are executable (`chmod +x *.sh`)
- [ ] Ports 5000, 6379, 8086 are free
- [ ] At least 2GB RAM available

---

**Happy Trading! 🚀**
