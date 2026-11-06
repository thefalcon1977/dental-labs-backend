#!/bin/bash
# OWASP ZAP dynamic security testing script
# Requires OWASP ZAP to be installed and the application to be running

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ZAP_HOST="${ZAP_HOST:-localhost}"
ZAP_PORT="${ZAP_PORT:-8080}"
TARGET_URL="${TARGET_URL:-http://localhost:8000}"
REPORTS_DIR="security-reports"
ZAP_API_KEY="${ZAP_API_KEY:-}"

# Create reports directory
mkdir -p "$REPORTS_DIR"

echo -e "${GREEN}Starting OWASP ZAP dynamic security scan...${NC}"

# Check if ZAP is running
if ! curl -s "http://${ZAP_HOST}:${ZAP_PORT}/" > /dev/null 2>&1; then
    echo -e "${RED}Error: OWASP ZAP is not running on ${ZAP_HOST}:${ZAP_PORT}${NC}"
    echo -e "${YELLOW}Please start ZAP first:${NC}"
    echo -e "  docker run -d -p ${ZAP_PORT}:8080 owasp/zap2docker-stable"
    echo -e "  or install and run ZAP locally"
    exit 1
fi

# Check if target application is running
if ! curl -s "$TARGET_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}Error: Target application is not running on ${TARGET_URL}${NC}"
    echo -e "${YELLOW}Please start your application first${NC}"
    exit 1
fi

# Build API URL
if [ -n "$ZAP_API_KEY" ]; then
    API_URL="http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/action/?apikey=${ZAP_API_KEY}"
else
    API_URL="http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/action/"
fi

echo -e "${YELLOW}Target URL: ${TARGET_URL}${NC}"
echo -e "${YELLOW}ZAP API: http://${ZAP_HOST}:${ZAP_PORT}${NC}"

# Start spider scan
echo -e "${YELLOW}[1/3] Starting spider scan...${NC}"
SPIDER_SCAN_ID=$(curl -s "${API_URL}spiderAction/scan/?url=${TARGET_URL}" | grep -o '"scan":"[^"]*"' | cut -d'"' -f4)
echo -e "${GREEN}Spider scan started (ID: ${SPIDER_SCAN_ID})${NC}"

# Wait for spider scan to complete
echo -e "${YELLOW}Waiting for spider scan to complete...${NC}"
while true; do
    STATUS=$(curl -s "${API_URL}spiderAction/status/?scanId=${SPIDER_SCAN_ID}" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    if [ "$STATUS" = "100" ]; then
        break
    fi
    sleep 2
done
echo -e "${GREEN}✓ Spider scan complete${NC}"

# Start active scan
echo -e "${YELLOW}[2/3] Starting active scan...${NC}"
ACTIVE_SCAN_ID=$(curl -s "${API_URL}ascanAction/scan/?url=${TARGET_URL}" | grep -o '"scan":"[^"]*"' | cut -d'"' -f4)
echo -e "${GREEN}Active scan started (ID: ${ACTIVE_SCAN_ID})${NC}"

# Wait for active scan to complete
echo -e "${YELLOW}Waiting for active scan to complete (this may take several minutes)...${NC}"
while true; do
    STATUS=$(curl -s "${API_URL}ascanAction/status/?scanId=${ACTIVE_SCAN_ID}" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    if [ "$STATUS" = "100" ]; then
        break
    fi
    sleep 5
done
echo -e "${GREEN}✓ Active scan complete${NC}"

# Generate reports
echo -e "${YELLOW}[3/3] Generating reports...${NC}"

# HTML report
curl -s "${API_URL}core/other/htmlreport/" > "$REPORTS_DIR/zap-report.html"

# JSON report
curl -s "${API_URL}core/other/jsonreport/" > "$REPORTS_DIR/zap-report.json"

# XML report
curl -s "${API_URL}core/other/xmlreport/" > "$REPORTS_DIR/zap-report.xml"

echo -e "${GREEN}✓ Reports generated${NC}"

# Summary
echo -e "\n${GREEN}=== OWASP ZAP Scan Summary ===${NC}"
echo -e "Reports saved to: ${YELLOW}$REPORTS_DIR/${NC}"
echo -e "\n${YELLOW}Report files:${NC}"
ls -lh "$REPORTS_DIR" | grep "zap-report" || true

echo -e "\n${GREEN}OWASP ZAP scan complete!${NC}"
echo -e "${YELLOW}Open $REPORTS_DIR/zap-report.html in your browser to view the full report.${NC}"
