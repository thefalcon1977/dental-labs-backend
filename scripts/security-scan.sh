#!/bin/bash
# Security scanning script
# Run all security tools and generate reports

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create reports directory
REPORTS_DIR="security-reports"
mkdir -p "$REPORTS_DIR"

echo -e "${GREEN}Starting security scan...${NC}"

# 1. Bandit - Static security analysis
echo -e "${YELLOW}[1/5] Running Bandit...${NC}"
bandit -c .bandit -r apps -f json -o "$REPORTS_DIR/bandit-report.json" || true
bandit -c .bandit -r apps -f txt -o "$REPORTS_DIR/bandit-report.txt" || true
echo -e "${GREEN}✓ Bandit scan complete${NC}"

# 2. Safety - Dependency vulnerability scanning
echo -e "${YELLOW}[2/5] Running Safety...${NC}"
safety check --json > "$REPORTS_DIR/safety-report.json" 2>&1 || true
safety check > "$REPORTS_DIR/safety-report.txt" 2>&1 || true
echo -e "${GREEN}✓ Safety scan complete${NC}"

# 3. pip-audit - Dependency vulnerability scanning
echo -e "${YELLOW}[3/5] Running pip-audit...${NC}"
pip-audit --format json --output "$REPORTS_DIR/pip-audit-report.json" --desc on || true
pip-audit --format columns --output "$REPORTS_DIR/pip-audit-report.txt" --desc on || true
echo -e "${GREEN}✓ pip-audit scan complete${NC}"

# 4. Semgrep - Pattern-based security scanning
echo -e "${YELLOW}[4/5] Running Semgrep...${NC}"
semgrep --config .semgrep.yml --json --output "$REPORTS_DIR/semgrep-report.json" || true
semgrep --config .semgrep.yml --output "$REPORTS_DIR/semgrep-report.txt" || true
echo -e "${GREEN}✓ Semgrep scan complete${NC}"

# 5. Summary
echo -e "\n${GREEN}=== Security Scan Summary ===${NC}"
echo -e "Reports saved to: ${YELLOW}$REPORTS_DIR/${NC}"
echo -e "\n${YELLOW}Report files:${NC}"
ls -lh "$REPORTS_DIR" | grep -E "\.(json|txt)$" || true

echo -e "\n${GREEN}Security scan complete!${NC}"
echo -e "${YELLOW}Note: OWASP ZAP requires a running application and is better suited for CI/CD.${NC}"
