#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "======================================================================"
echo "🚀 VELOX TRADING SYSTEM - INTEGRATED STARTUP"
echo "======================================================================"
echo "Services: Kafka + InfluxDB + Redis + Flask"
echo "======================================================================"
echo -e "${NC}"

# Step 1: Check Docker
echo -e "\n${YELLOW}🐳 Step 1: Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon not running. Please start Docker.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"

# Step 2: Start Docker Services
echo -e "\n${YELLOW}🔧 Step 2: Starting Docker services (Kafka, InfluxDB, Redis)...${NC}"
docker compose up -d

# Wait for services to be healthy
echo -e "\n${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 5

# Check Redis
echo -n "Checking Redis... "
if docker exec velox-redis redis-cli ping &> /dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
fi

# Check InfluxDB
echo -n "Checking InfluxDB... "
if curl -s http://localhost:8086/health | grep -q "pass" 2>/dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${YELLOW}⚠️  (may take a few more seconds)${NC}"
fi

# Check Kafka
echo -n "Checking Kafka... "
if docker exec velox-kafka kafka-broker-api-versions --bootstrap-server localhost:9092 &> /dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${YELLOW}⚠️  (may take a few more seconds)${NC}"
fi

# Step 3: Install Python Dependencies
echo -e "\n${YELLOW}📦 Step 3: Checking Python dependencies...${NC}"
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing/updating dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements_integrated.txt

echo -e "${GREEN}✅ Dependencies installed${NC}"

# Step 4: Create Kafka Topics
echo -e "\n${YELLOW}📡 Step 4: Creating Kafka topics...${NC}"
docker exec velox-kafka kafka-topics --create --if-not-exists \
    --bootstrap-server localhost:9092 \
    --topic velox-events \
    --partitions 3 \
    --replication-factor 1 2>/dev/null

docker exec velox-kafka kafka-topics --create --if-not-exists \
    --bootstrap-server localhost:9092 \
    --topic velox-ticks \
    --partitions 3 \
    --replication-factor 1 2>/dev/null

docker exec velox-kafka kafka-topics --create --if-not-exists \
    --bootstrap-server localhost:9092 \
    --topic velox-signals \
    --partitions 1 \
    --replication-factor 1 2>/dev/null

docker exec velox-kafka kafka-topics --create --if-not-exists \
    --bootstrap-server localhost:9092 \
    --topic velox-trades \
    --partitions 1 \
    --replication-factor 1 2>/dev/null

echo -e "${GREEN}✅ Kafka topics created${NC}"

# Step 5: Display Service URLs
echo -e "\n${BLUE}======================================================================"
echo "📊 Service URLs:"
echo "======================================================================"
echo "Dashboard:  http://localhost:5000"
echo "InfluxDB:   http://localhost:8086"
echo "  Username: admin"
echo "  Password: veloxinflux123"
echo "  Org:      velox"
echo "  Bucket:   trading"
echo "Redis:      localhost:6379"
echo "Kafka:      localhost:9092"
echo "======================================================================"
echo -e "${NC}"

# Step 6: Start VELOX Dashboard
echo -e "\n${YELLOW}🎯 Step 6: Starting VELOX Integrated Dashboard...${NC}"
echo -e "${GREEN}Starting with date: 2020-09-15${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}\n"

echo -e "${BLUE}What to expect:${NC}"
echo "  • All ticks streamed to Kafka (velox-ticks topic)"
echo "  • Signals published to Kafka (velox-signals topic)"
echo "  • Trades published to Kafka (velox-trades topic)"
echo "  • Historical data stored in InfluxDB"
echo "  • Real-time data cached in Redis"
echo "  • Dashboard shows service status"
echo ""

# Start dashboard
python3 dashboard_integrated.py

# Cleanup on exit
echo -e "\n${YELLOW}Stopping services...${NC}"
docker compose stop
echo -e "${GREEN}✅ Services stopped${NC}"
