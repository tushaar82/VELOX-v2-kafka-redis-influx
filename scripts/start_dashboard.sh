#!/bin/bash

# VELOX Dashboard Startup Script

set -e

echo "======================================"
echo "VELOX Analytics Dashboard Startup"
echo "======================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python dependencies
echo -e "${BLUE}Checking Python dependencies...${NC}"
if ! pip list | grep -q fastapi; then
    echo -e "${RED}Installing Python dependencies...${NC}"
    pip install -r requirements-dashboard.txt
fi

# Start REST API server in background
echo -e "${BLUE}Starting REST API server on port 8000...${NC}"
cd src/dashboard/api
python rest_api.py &
REST_PID=$!
echo -e "${GREEN}REST API started (PID: $REST_PID)${NC}"

# Start WebSocket server in background
echo -e "${BLUE}Starting WebSocket server on port 8765...${NC}"
python websocket_server.py &
WS_PID=$!
echo -e "${GREEN}WebSocket server started (PID: $WS_PID)${NC}"

# Go to dashboard directory
cd ../../../dashboard

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing Node.js dependencies...${NC}"
    npm install
fi

# Start React dev server
echo -e "${BLUE}Starting React development server on port 3000...${NC}"
npm run dev &
REACT_PID=$!

echo ""
echo -e "${GREEN}======================================"
echo "Dashboard started successfully!"
echo "======================================"
echo ""
echo "Services running:"
echo "  - REST API:     http://localhost:8000"
echo "  - WebSocket:    ws://localhost:8765"
echo "  - Dashboard:    http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"
echo -e "${NC}"

# Trap Ctrl+C to kill all processes
trap 'echo -e "\n${RED}Stopping all services...${NC}"; kill $REST_PID $WS_PID $REACT_PID 2>/dev/null; exit' INT

# Wait for any process to exit
wait
