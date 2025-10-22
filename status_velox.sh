#!/bin/bash
# VELOX Trading System - Status Check

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "======================================================================"
echo "📊 VELOX TRADING SYSTEM - STATUS"
echo "======================================================================"
echo -e "${NC}"

# Check Redis
echo -e "\n${YELLOW}🔴 Redis:${NC}"
if nc -z localhost 6379 2>/dev/null; then
    echo -e "${GREEN}✅ Running on port 6379${NC}"
    docker exec velox-redis redis-cli ping 2>/dev/null | grep -q PONG && echo -e "${GREEN}   Responding to commands${NC}"
else
    echo -e "${RED}❌ Not running${NC}"
fi

# Check InfluxDB
echo -e "\n${YELLOW}📊 InfluxDB:${NC}"
if nc -z localhost 8086 2>/dev/null; then
    echo -e "${GREEN}✅ Running on port 8086${NC}"
    curl -s http://localhost:8086/health | grep -q "pass" && echo -e "${GREEN}   Health check passed${NC}"
else
    echo -e "${RED}❌ Not running${NC}"
fi

# Check Dashboard
echo -e "\n${YELLOW}🎯 Dashboard:${NC}"
if nc -z localhost 5000 2>/dev/null; then
    echo -e "${GREEN}✅ Running on port 5000${NC}"
    echo -e "${GREEN}   URL: http://localhost:5000${NC}"
else
    echo -e "${RED}❌ Not running${NC}"
fi

# Check SQLite
echo -e "\n${YELLOW}💾 SQLite:${NC}"
if [ -f "data/velox_trades.db" ]; then
    SIZE=$(ls -lh data/velox_trades.db | awk '{print $5}')
    echo -e "${GREEN}✅ Database exists (${SIZE})${NC}"
else
    echo -e "${YELLOW}⚠️  Database not created yet${NC}"
fi

# Check Docker containers
echo -e "\n${YELLOW}🐳 Docker Containers:${NC}"
docker ps --filter "name=velox" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null

# Check logs
echo -e "\n${YELLOW}📝 Recent Logs:${NC}"
if [ -d "logs" ]; then
    echo -e "${GREEN}✅ Log directory exists${NC}"
    ls -lh logs/*.log 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}'
else
    echo -e "${YELLOW}⚠️  No logs yet${NC}"
fi

echo -e "\n${BLUE}======================================================================"
echo -e "${NC}"
