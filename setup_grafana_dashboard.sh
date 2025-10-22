#!/bin/bash

# VELOX Grafana Dashboard Setup Script
# This script sets up and starts the Grafana dashboard for trade verification

set -e

echo "========================================"
echo "VELOX Grafana Dashboard Setup"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed${NC}"
    echo "Please install docker-compose first: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓${NC} docker-compose is installed"

# Check if grafana directories exist
if [ ! -d "grafana/provisioning" ]; then
    echo -e "${RED}Error: Grafana provisioning directory not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Grafana provisioning directories found"

# Stop any running containers
echo ""
echo "Stopping any existing containers..."
docker-compose down 2>/dev/null || true

# Start infrastructure services
echo ""
echo "Starting infrastructure services..."
echo "  - Redis (port 6379)"
echo "  - InfluxDB (port 8086)"
echo "  - Kafka & Zookeeper (ports 9092, 2181)"
echo "  - Grafana (port 3000)"
echo ""

docker-compose up -d redis influxdb kafka zookeeper grafana

# Wait for services to be healthy
echo ""
echo "Waiting for services to be ready..."
sleep 5

# Check service status
echo ""
echo "Checking service status..."

# Check Redis
if docker-compose ps redis | grep -q "Up"; then
    echo -e "${GREEN}✓${NC} Redis is running"
else
    echo -e "${RED}✗${NC} Redis failed to start"
fi

# Check InfluxDB
if docker-compose ps influxdb | grep -q "Up"; then
    echo -e "${GREEN}✓${NC} InfluxDB is running"
else
    echo -e "${RED}✗${NC} InfluxDB failed to start"
fi

# Check Kafka
if docker-compose ps kafka | grep -q "Up"; then
    echo -e "${GREEN}✓${NC} Kafka is running"
else
    echo -e "${RED}✗${NC} Kafka failed to start"
fi

# Check Grafana
if docker-compose ps grafana | grep -q "Up"; then
    echo -e "${GREEN}✓${NC} Grafana is running"
else
    echo -e "${RED}✗${NC} Grafana failed to start"
fi

# Wait for Grafana to fully initialize
echo ""
echo "Waiting for Grafana to initialize (this may take 10-15 seconds)..."
sleep 10

# Test Grafana health
echo ""
echo "Testing Grafana health endpoint..."
for i in {1..10}; do
    if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Grafana is healthy and responding"
        break
    else
        if [ $i -eq 10 ]; then
            echo -e "${YELLOW}⚠${NC} Grafana is starting but not fully ready yet. Please wait a moment."
        else
            sleep 2
        fi
    fi
done

# Check if InfluxDB bucket exists
echo ""
echo "Verifying InfluxDB configuration..."
if docker exec velox-influxdb influx bucket list --org velox --token velox-super-secret-token 2>/dev/null | grep -q "trading"; then
    echo -e "${GREEN}✓${NC} InfluxDB bucket 'trading' exists"
else
    echo -e "${YELLOW}⚠${NC} InfluxDB bucket 'trading' not found. It will be created on first run."
fi

# Summary
echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Services are running at:"
echo "  - Grafana Dashboard:  ${GREEN}http://localhost:3000${NC}"
echo "  - InfluxDB:           http://localhost:8086"
echo "  - Redis:              localhost:6379"
echo "  - Kafka:              localhost:9092"
echo ""
echo "Grafana Login:"
echo "  Username: ${GREEN}admin${NC}"
echo "  Password: ${GREEN}velox123${NC}"
echo ""
echo "Dashboard Location:"
echo "  ${GREEN}VELOX Trade Verification Dashboard${NC}"
echo ""
echo "Next Steps:"
echo "  1. Open ${GREEN}http://localhost:3000${NC} in your browser"
echo "  2. Login with admin/velox123"
echo "  3. Look for 'VELOX Trade Verification Dashboard' in the dashboards list"
echo "  4. Run a simulation to populate data: ${YELLOW}python3 velox.py --date 2024-01-15${NC}"
echo ""
echo "To view container logs:"
echo "  ${YELLOW}docker-compose logs -f grafana${NC}     (Grafana logs)"
echo "  ${YELLOW}docker-compose logs -f influxdb${NC}    (InfluxDB logs)"
echo ""
echo "To stop all services:"
echo "  ${YELLOW}docker-compose down${NC}"
echo ""
echo "For troubleshooting, see: ${GREEN}grafana/README.md${NC}"
echo ""
