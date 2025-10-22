#!/bin/bash
# VELOX Trading System - Stop Script

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "======================================================================"
echo "🛑 VELOX TRADING SYSTEM - SHUTDOWN"
echo "======================================================================"
echo -e "${NC}"

# Stop dashboard
echo -e "\n${YELLOW}📊 Stopping Dashboard...${NC}"
pkill -f dashboard_final.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dashboard stopped${NC}"
else
    echo -e "${YELLOW}⚠️  Dashboard was not running${NC}"
fi

# Stop Docker services
echo -e "\n${YELLOW}🐳 Stopping Docker services...${NC}"
docker compose stop redis influxdb
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker services stopped${NC}"
else
    echo -e "${RED}❌ Failed to stop Docker services${NC}"
fi

echo -e "\n${GREEN}✅ VELOX shutdown complete${NC}"
