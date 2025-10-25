# VELOX Production Safety Guide

## 🚨 CRITICAL SAFETY FEATURES

### 1. Order Deduplication (Prevents Duplicate Orders)

**What it does:**
- Prevents the same order from being placed multiple times
- Uses Redis to track pending orders
- Checks for existing positions before opening new ones
- 5-second time window to prevent rapid duplicate signals

**Configuration:**
```yaml
risk:
  enable_deduplication: true  # MUST BE TRUE
  dedup_window_seconds: 5
```

**How it works:**
```
Signal Generated → Check Redis for pending order
                 → Check if position already exists
                 → If duplicate detected → REJECT
                 → If unique → APPROVE
```

### 2. Fixed Lot Size (Mandatory for Production)

**What it does:**
- Enforces a fixed quantity for every trade
- Overrides strategy-calculated lot sizes
- Prevents accidental large orders

**Configuration:**
```yaml
risk:
  fixed_lot_size: 1  # Trade only 1 share per order
```

**Example:**
```
Strategy calculates: Buy 10 shares
Fixed lot size:      1 share
Actual order:        Buy 1 share ✓
```

### 3. Emergency Exit Manager (Auto-Close All Positions)

**What it does:**
- Monitors daily P&L in real-time
- Automatically closes ALL positions when loss limit is breached
- Disables trading for the rest of the day
- Sends critical alerts

**Configuration:**
```yaml
risk:
  max_daily_loss: 2000  # Rs. 2000 absolute limit
  max_daily_loss_pct: 2.0  # 2% of capital
  initial_capital: 100000
```

**Trigger Conditions:**
- Daily loss reaches Rs. 2000 (whichever comes first)
- OR Daily loss reaches 2% of capital

**What happens:**
1. Emergency exit triggered
2. All open positions closed immediately
3. Trading disabled until next day
4. Critical logs generated
5. Dashboard shows emergency status

### 4. Enhanced Risk Manager

**Multiple layers of protection:**

1. **Emergency Exit Check** - Trading disabled if loss limit breached
2. **Deduplication Check** - No duplicate orders
3. **Position Existence Check** - No duplicate positions
4. **Position Size Limit** - Maximum Rs. per position
5. **Positions Per Strategy** - Max positions per strategy
6. **Total Position Limit** - Max total open positions
7. **Daily Loss Check** - Real-time P&L monitoring

**Rejection Flow:**
```
Signal → Emergency Exit? → Duplicate? → Position Exists?
       → Size Limit? → Strategy Limit? → Total Limit?
       → Daily Loss? → APPROVE/REJECT
```

## ⚙️ Production Configuration

### Required Settings

**`config/system_production.yaml`:**

```yaml
system:
  broker:
    type: simulated  # Change for live: zerodha | upstox
    capital: 100000  # Your actual capital

  risk:
    # CRITICAL - Set these appropriately
    max_daily_loss: 2000  # Rs. 2000 loss limit
    max_daily_loss_pct: 2.0  # 2% loss limit
    initial_capital: 100000  # Your capital
    fixed_lot_size: 1  # MANDATORY - 1 share per trade
    enable_deduplication: true  # MANDATORY

    # Position limits
    max_position_size: 5000  # Rs. 5000 per position
    max_positions_per_strategy: 2
    max_total_positions: 3
```

### Pre-Production Checklist

- [ ] `fixed_lot_size` is set (NOT null)
- [ ] `max_daily_loss` matches your risk tolerance
- [ ] `enable_deduplication` is `true`
- [ ] `initial_capital` matches actual capital
- [ ] `max_total_positions` is conservative (3-5)
- [ ] Broker type is correct
- [ ] Redis is running and accessible
- [ ] InfluxDB is running for monitoring
- [ ] Dashboard is accessible
- [ ] Test with simulated broker first
- [ ] Backup strategy is in place

## 🎯 Usage

### Starting the System

```bash
# Start with production config
python src/main.py \
  --config config/system_production.yaml \
  --date 2024-01-15 \
  --speed 1.0
```

### Monitoring

```bash
# Start dashboard
./scripts/start_dashboard.sh

# Access at:
# http://localhost:3000
```

**Watch for:**
- Daily P&L approaching limit
- Number of open positions
- Order rejections
- Emergency exit status

### Emergency Situations

**If emergency exit is triggered:**

1. System automatically closes all positions
2. Trading is disabled for the day
3. Check logs: `logs/production/risk_manager.log`
4. Review dashboard for details
5. Analyze what went wrong
6. Adjust strategies or limits

**Manual Emergency Exit:**

```python
# In case you need to manually trigger
from src.core.emergency_exit_manager import EmergencyExitManager

emergency_exit = risk_manager.get_emergency_exit_manager()

# Get current status
status = emergency_exit.get_risk_status()
print(status)

# View daily summary
summary = emergency_exit.get_daily_summary()
print(summary)
```

## 📊 Monitoring & Alerts

### Dashboard Monitoring

1. **Open Positions** - Real-time P&L per position
2. **Order Verification** - Check for unclosed orders
3. **Strategy Metrics** - Win rate, profit factor
4. **System Status** - Database health, connection status

### Log Files

```
logs/production/
├── risk_manager.log      # All risk decisions
├── order_manager.log     # Order execution
├── emergency_exit.log    # Emergency exit events
└── system.log            # General system logs
```

### Key Log Patterns

**Order Deduplication:**
```
[RISK_CHECK] strategy/symbol: REJECTED - Duplicate order prevented
[RISK_CHECK] strategy/symbol: REJECTED - Position already exists
```

**Emergency Exit:**
```
🚨 EMERGENCY EXIT TRIGGERED 🚨
Daily P&L: -2150.00
Max Daily Loss: -2000.00
```

**Fixed Lot Size:**
```
[RISK_CHECK] strategy/symbol: Lot size adjusted 10 -> 1 (fixed lot size)
```

## 🔧 Troubleshooting

### Problem: Too many order rejections

**Possible causes:**
1. Deduplication window too long
2. Strategies generating rapid signals
3. Position limits too strict

**Solution:**
```yaml
# Adjust dedup window
dedup_window_seconds: 3  # Reduce from 5 to 3

# Or increase position limits
max_positions_per_strategy: 3  # Increase from 2
```

### Problem: Emergency exit triggered too early

**Possible causes:**
1. Loss limit too strict for capital
2. Volatile market conditions
3. Strategy drawdown larger than expected

**Solution:**
```yaml
# Adjust loss limits
max_daily_loss: 3000  # Increase from 2000
max_daily_loss_pct: 3.0  # Increase from 2.0
```

### Problem: Orders not executing

**Check:**
1. Is emergency exit triggered?
2. Are position limits reached?
3. Is deduplication blocking orders?
4. Check risk_manager logs

```bash
# View recent rejections
grep "REJECTED" logs/production/risk_manager.log | tail -20
```

## 🎓 Best Practices

### 1. Start Conservative

```yaml
# First week of production
max_daily_loss: 1000  # Very conservative
fixed_lot_size: 1  # Minimum lot size
max_total_positions: 2  # Few positions
```

### 2. Gradually Increase

After proving system stability:
```yaml
# After 1 month of successful trading
max_daily_loss: 2000
fixed_lot_size: 2  # or keep at 1
max_total_positions: 3
```

### 3. Monitor Daily

- Check dashboard every hour
- Review logs at end of day
- Track P&L vs expectations
- Analyze order rejections

### 4. Regular Backups

```bash
# Backup databases daily
./scripts/backup_databases.sh

# Keep trade logs
cp -r logs/production logs/backup/$(date +%Y%m%d)
```

### 5. Test Everything

Before production:
```bash
# Run with simulated broker
# Test emergency exit
# Test duplicate order prevention
# Test fixed lot sizes
# Verify dashboard works
```

## 🚀 Going Live Checklist

- [ ] Tested thoroughly with simulated broker
- [ ] All safety features enabled
- [ ] Fixed lot size set appropriately
- [ ] Loss limits match risk tolerance
- [ ] Dashboard is accessible and monitored
- [ ] Alerts/notifications configured
- [ ] Broker API credentials verified
- [ ] Capital amount is correct
- [ ] Backup plan in place
- [ ] Know how to stop system immediately
- [ ] Emergency contact numbers ready
- [ ] Legal/regulatory requirements met

## 📞 Emergency Contacts

In case of system malfunction:

1. **Stop trading immediately:**
   ```bash
   pkill -f "python src/main.py"
   ```

2. **Close all positions manually** via broker platform

3. **Check system logs** for errors

4. **Contact support** if needed

## ⚠️ Disclaimers

- This system is for educational purposes
- No guarantees of profit
- Trading involves risk of loss
- Test thoroughly before live trading
- Start with minimum capital
- Monitor constantly
- Have a stop-loss plan
- Know your risk tolerance

---

**Remember: The best safety feature is YOU monitoring the system!**
