#!/bin/bash
# Quick script to fix security vulnerabilities
# Updates vulnerable packages to fixed versions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting vulnerability remediation...${NC}"

# 1. Update python-multipart (direct dependency, CVE-2026-24486)
echo -e "${YELLOW}[1/5] Updating python-multipart (0.0.21 → 0.0.22)...${NC}"
CURRENT_VERSION=$(poetry show python-multipart | grep "version" | awk '{print $3}')
echo -e "Current version: ${CURRENT_VERSION}"
poetry update python-multipart
NEW_VERSION=$(poetry show python-multipart | grep "version" | awk '{print $3}')
echo -e "${GREEN}✓ python-multipart updated: ${CURRENT_VERSION} → ${NEW_VERSION}${NC}"

# 2. Update urllib3 via parent packages (CVE-2026-21441)
echo -e "${YELLOW}[2/5] Updating urllib3 via httpx/requests/botocore (2.6.2 → 2.6.3+)...${NC}"
CURRENT_VERSION=$(poetry show urllib3 | grep "version" | awk '{print $3}')
echo -e "Current version: ${CURRENT_VERSION}"
poetry update httpx requests botocore aioboto3 || {
    echo -e "${YELLOW}Warning: Some urllib3 dependencies may not have updates available${NC}"
}
NEW_VERSION=$(poetry show urllib3 | grep "version" | awk '{print $3}')
echo -e "${GREEN}✓ urllib3 updated: ${CURRENT_VERSION} → ${NEW_VERSION}${NC}"

# 3. Update filelock (CVE-2026-22701)
echo -e "${YELLOW}[3/5] Updating filelock via safety/cachecontrol/virtualenv (3.20.1 → 3.20.3+)...${NC}"
CURRENT_VERSION=$(poetry show filelock | grep "version" | awk '{print $3}')
echo -e "Current version: ${CURRENT_VERSION}"
poetry update safety cachecontrol virtualenv || {
    echo -e "${YELLOW}Warning: Some filelock dependencies may not have updates available${NC}"
}
NEW_VERSION=$(poetry show filelock | grep "version" | awk '{print $3}')
echo -e "${GREEN}✓ filelock updated: ${CURRENT_VERSION} → ${NEW_VERSION}${NC}"

# 4. Update virtualenv (dev dependency, CVE-2026-22702)
echo -e "${YELLOW}[4/5] Updating virtualenv (20.35.4 → 20.36.2+)...${NC}"
CURRENT_VERSION=$(poetry show virtualenv | grep "version" | awk '{print $3}')
echo -e "Current version: ${CURRENT_VERSION}"
poetry update virtualenv || {
    echo -e "${YELLOW}Warning: Failed to update virtualenv (may not be critical)${NC}"
}
NEW_VERSION=$(poetry show virtualenv | grep "version" | awk '{print $3}')
echo -e "${GREEN}✓ virtualenv updated: ${CURRENT_VERSION} → ${NEW_VERSION}${NC}"

# 5. General update to catch any remaining transitive dependencies
echo -e "${YELLOW}[5/5] Running general update for remaining dependencies...${NC}"
poetry update || {
    echo -e "${YELLOW}Warning: Some dependencies may not have updates available${NC}"
}
echo -e "${GREEN}✓ General update complete${NC}"

# 6. Verify updates
echo -e "\n${YELLOW}Verifying updates...${NC}"
echo -e "\n${GREEN}Final versions:${NC}"
poetry show python-multipart | grep "version" || true
poetry show urllib3 | grep "version" || true
poetry show filelock | grep "version" || true
poetry show virtualenv | grep "version" || true

# 6. Re-run security scan
echo -e "\n${YELLOW}Re-running security scans...${NC}"
./scripts/security-scan.sh

echo -e "\n${GREEN}=== Vulnerability Remediation Complete ===${NC}"
echo -e "${YELLOW}Note: ecdsa (CVE-2024-23342) has no fix available.${NC}"
echo -e "${YELLOW}Review docs/security-vulnerabilities-plan.md for details.${NC}"
