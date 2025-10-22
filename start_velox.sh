#!/bin/bash
# VELOX Trading System - Startup Script
# Updated with realistic trading parameters and functional trailing SL

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "======================================================================"
echo "🚀 VELOX TRADING SYSTEM - STARTUP (v2.1 - Supertrend Strategy)"
echo "======================================================================"
echo -e "${NC}"

# Function to check if a service is running
check_service() {
    local service=$1
    local port=$2
    if nc -z localhost $port 2>/dev/null; then
        echo -e "${GREEN}✅ $service is running on port $port${NC}"
        return 0
    else
        echo -e "${RED}❌ $service is not running on port $port${NC}"
        return 1
    fi
}

# Step 1: Check Docker
echo -e "\n${YELLOW}📦 Step 1: Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker is installed${NC}"

# Step 2: Start Docker services
echo -e "\n${YELLOW}🐳 Step 2: Starting Docker services...${NC}"
docker compose up -d redis influxdb

# Wait for services to be ready
echo -e "\n${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 5

# Step 3: Check services
echo -e "\n${YELLOW}🔍 Step 3: Checking services...${NC}"
check_service "Redis" 6379 || echo -e "${YELLOW}⚠️  Redis not available, will run without cache${NC}"
check_service "InfluxDB" 8086 || echo -e "${YELLOW}⚠️  InfluxDB not available, will run without time-series${NC}"

# Step 4: Check Python dependencies
echo -e "\n${YELLOW}🐍 Step 4: Checking Python dependencies...${NC}"
python3 -c "import redis, influxdb_client, colorlog" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All Python dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠️  Some dependencies missing. Installing...${NC}"
    pip install redis influxdb-client colorlog -q
fi

# Step 5: Run tests (optional)
if [ "$1" == "--test" ]; then
    echo -e "\n${YELLOW}🧪 Step 5: Running tests...${NC}"
    ./run_all_tests.sh
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Tests failed. Please fix issues before running.${NC}"
        exit 1
    fi
fi

# Step 6: Start VELOX Dashboard
echo -e "\n${YELLOW}🎯 Step 6: Starting VELOX Dashboard...${NC}"
echo -e "${BLUE}======================================================================"
echo "📊 Dashboard: http://localhost:5000"
echo "📅 Date: 2020-09-15 (use --date YYYY-MM-DD to change)"
echo "⚡ Speed: 100x (realistic simulation)"
echo "⏱️  Timeframe: 3-minute candles"
echo "🎯 Ticks: 10 per candle (every 18 seconds)"
echo "📈 Strategy: Supertrend (10, 3)"
echo "   • ATR Period: 10"
echo "   • ATR Multiplier: 3"
echo "   • Symbols: 5 (ABB, ADANIENT, AMBER, BANKINDIA, BATAINDIA)"
echo "   • Min Hold: 5 minutes"
echo "======================================================================"
echo -e "${NC}"

# Parse arguments
DATE="2020-09-15"
PORT="5000"

while [[ $# -gt 0 ]]; do
    case $1 in
        --date)
            DATE="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --test)
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--test] [--date YYYY-MM-DD] [--port PORT]"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}Starting with date: $DATE, port: ${PORT}${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}\n"

# Display what to expect
echo -e "${BLUE}What to expect:${NC}"
echo "  • Supertrend strategy on 3-minute candles"
echo "  • BUY when price crosses above Supertrend (bullish)"
echo "  • SELL when price crosses below Supertrend (bearish)"
echo "  • Simple trend-following with clear signals"
echo "  • Look for these log messages:"
echo "    📊 BUY SIGNAL: Supertrend bullish crossover"
echo "    📊 SELL SIGNAL: Supertrend bearish crossover"
echo ""

# Start dashboard (using dashboard_working.py with all fixes)
python3 dashboard_working.py
