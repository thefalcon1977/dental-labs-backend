# Security scanning script for Windows PowerShell
# Run all security tools and generate reports

$ErrorActionPreference = "Stop"

# Colors for output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

# Create reports directory
$REPORTS_DIR = "security-reports"
if (-not (Test-Path $REPORTS_DIR)) {
    New-Item -ItemType Directory -Path $REPORTS_DIR | Out-Null
}

Write-ColorOutput Green "Starting security scan..."

# 1. Bandit - Static security analysis
Write-ColorOutput Yellow "[1/5] Running Bandit..."
try {
    bandit -c .bandit -r apps -f json -o "$REPORTS_DIR\bandit-report.json" 2>&1 | Out-Null
    bandit -c .bandit -r apps -f txt -o "$REPORTS_DIR\bandit-report.txt" 2>&1 | Out-Null
    Write-ColorOutput Green "✓ Bandit scan complete"
} catch {
    Write-ColorOutput Red "Bandit scan failed: $_"
}

# 2. Safety - Dependency vulnerability scanning
Write-ColorOutput Yellow "[2/5] Running Safety..."
try {
    safety check --json > "$REPORTS_DIR\safety-report.json" 2>&1
    safety check --text > "$REPORTS_DIR\safety-report.txt" 2>&1
    Write-ColorOutput Green "✓ Safety scan complete"
} catch {
    Write-ColorOutput Red "Safety scan failed: $_"
}

# 3. pip-audit - Dependency vulnerability scanning
Write-ColorOutput Yellow "[3/5] Running pip-audit..."
try {
    pip-audit --format json --output "$REPORTS_DIR\pip-audit-report.json" --desc on 2>&1 | Out-Null
    pip-audit --format columns --output "$REPORTS_DIR\pip-audit-report.txt" --desc on 2>&1 | Out-Null
    Write-ColorOutput Green "✓ pip-audit scan complete"
} catch {
    Write-ColorOutput Red "pip-audit scan failed: $_"
}

# 4. Semgrep - Pattern-based security scanning
Write-ColorOutput Yellow "[4/5] Running Semgrep..."
try {
    semgrep --config .semgrep.yml --json --output "$REPORTS_DIR\semgrep-report.json" 2>&1 | Out-Null
    semgrep --config .semgrep.yml --output "$REPORTS_DIR\semgrep-report.txt" 2>&1 | Out-Null
    Write-ColorOutput Green "✓ Semgrep scan complete"
} catch {
    Write-ColorOutput Red "Semgrep scan failed: $_"
}

# 5. Summary
Write-ColorOutput Green "`n=== Security Scan Summary ==="
Write-ColorOutput Yellow "Reports saved to: $REPORTS_DIR\"
Write-ColorOutput Yellow "`nReport files:"
Get-ChildItem $REPORTS_DIR -Filter "*.json","*.txt" | Format-Table Name, Length -AutoSize

Write-ColorOutput Green "`nSecurity scan complete!"
Write-ColorOutput Yellow "Note: OWASP ZAP requires a running application and is better suited for CI/CD."
