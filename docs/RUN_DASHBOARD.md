# Running VELOX Dashboard with Different Dates

## 🚀 Quick Start

### Run with Default Date (2020-09-15):
```bash
python dashboard_final.py
```

### Run with Specific Date:
```bash
python dashboard_final.py --date 2020-09-16
python dashboard_final.py --date 2020-09-17
python dashboard_final.py --date 2022-05-11
```

### Run on Different Port:
```bash
python dashboard_final.py --date 2020-09-15 --port 5001
```

---

## 📅 Available Dates

### Date Range: **2015-02-02 to 2025-07-25**

### Good Test Dates:
- `2020-09-15` - Volatile day, good for testing
- `2020-09-16` - Follow-up day
- `2020-09-17` - Another active day
- `2022-05-11` - Recent data
- `2015-06-29` - Early data

---

## 🎯 Running Multiple Simulations

### Terminal 1:
```bash
python dashboard_final.py --date 2020-09-15 --port 5000
# Open: http://localhost:5000
```

### Terminal 2:
```bash
python dashboard_final.py --date 2020-09-16 --port 5001
# Open: http://localhost:5001
```

### Terminal 3:
```bash
python dashboard_final.py --date 2020-09-17 --port 5002
# Open: http://localhost:5002
```

---

## 📊 What to Expect

### Simulation Duration:
- **Speed:** 50x real-time
- **Ticks:** ~7,000-8,000 per day (3 symbols)
- **Duration:** 2-3 minutes per trading day
- **Candles:** ~370 per symbol

### Trading Activity:
- **Signals:** 5-15 per day
- **Orders:** 3-10 per day
- **Trades Closed:** 2-8 per day

---

## 🔍 Analyzing Results

### After Simulation Completes:
1. **Dashboard stays active** for review
2. **Closed Trades** table shows all trades
3. **Activity Logs** show complete history
4. **Final P&L** displayed in Account Summary

### Terminal Output:
```
📊 TRADING DAY SUMMARY
================================================================================
Ticks Processed: 7480
Orders Executed: 12
Trades Closed: 6
Final P&L: +$234.50 (+0.23%)
================================================================================
✓ Dashboard still running at http://localhost:5000
✓ Press Ctrl+C to stop the dashboard
```

---

## 💡 Tips

### 1. Compare Different Days:
```bash
# Run 3 different days side by side
python dashboard_final.py --date 2020-09-15 --port 5000 &
python dashboard_final.py --date 2020-09-16 --port 5001 &
python dashboard_final.py --date 2020-09-17 --port 5002 &
```

### 2. Find Profitable Days:
Test multiple dates and compare P&L

### 3. Strategy Testing:
Modify `config/strategies.yaml` and test on different dates

### 4. Backtesting:
Run simulations for consecutive days to see strategy performance

---

## 🛠️ Troubleshooting

### "No data found" Error:
- Check if date is within range (2015-02-02 to 2025-07-25)
- Ensure date format is YYYY-MM-DD
- Check if it's a trading day (not weekend/holiday)

### Port Already in Use:
```bash
# Use a different port
python dashboard_final.py --port 5001
```

### Simulation Stops Too Early:
- Check terminal for errors
- Verify data exists for all 3 symbols on that date
- Try a different date

---

## 📈 Example Workflow

### Day 1: Test Strategy
```bash
python dashboard_final.py --date 2020-09-15
# Review results, note P&L
```

### Day 2: Verify Consistency
```bash
python dashboard_final.py --date 2020-09-16
# Compare with Day 1
```

### Day 3: Optimize Parameters
```bash
# Edit config/strategies.yaml
# Adjust RSI thresholds, targets, etc.
python dashboard_final.py --date 2020-09-15
# Compare with original results
```

---

## 🎉 Happy Trading!

**Remember:** 
- Dashboard stays active after simulation
- Review closed trades for insights
- Test multiple dates for robust strategies
- Press Ctrl+C to stop dashboard

**Dashboard URL:** http://localhost:5000
