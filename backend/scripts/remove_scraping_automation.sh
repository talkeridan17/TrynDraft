#!/bin/bash
#
# Remove TrynDraft Scraping Automation
# =====================================
# Removes cron jobs for automated scraping
#
# Usage: ./scripts/remove_scraping_automation.sh
#

set -e

echo ""
echo "Removing TrynDraft scraping automation..."
echo ""

# Backup current crontab
crontab -l > /tmp/crontab_backup_before_remove_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Remove TrynDraft cron entries
crontab -l 2>/dev/null | grep -v "TrynDraft" | grep -v "run_scrapers.py" | crontab - 2>/dev/null || true

echo "✓ Cron jobs removed"
echo ""
echo "Backup saved to: /tmp/crontab_backup_before_remove_*"
echo ""
echo "To view remaining cron jobs:"
echo "  crontab -l"
echo ""
