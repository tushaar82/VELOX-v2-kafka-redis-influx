#!/bin/bash
# Run all VELOX tests

echo "======================================================================"
echo "🚀 RUNNING ALL VELOX TESTS"
echo "======================================================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Test 1: Redis + InfluxDB
echo -e "\n📊 Test 1: Redis + InfluxDB Integration..."
if python3 test_influx_redis.py > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# Test 2: SQLite
echo -e "\n📊 Test 2: SQLite Manager..."
if python3 test_sqlite.py > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# Test 3: Logging
echo -e "\n📊 Test 3: Structured Logging..."
if python3 test_logging.py > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# Test 4: DataManager
echo -e "\n📊 Test 4: Unified DataManager..."
if python3 test_data_manager.py > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# Test 5: Integration
echo -e "\n📊 Test 5: Integration Tests..."
if python3 test_integration.py > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}"
    ((FAILED++))
fi

# Summary
echo -e "\n======================================================================"
echo "📊 TEST SUMMARY"
echo "======================================================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo "======================================================================"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}⚠️  Some tests failed!${NC}"
    exit 1
fi
