#!/bin/bash
#
# Setup Automated Scraping for TrynDraft
# =======================================
# Sets up automated daily scraping using cron jobs
#
# Usage: ./scripts/setup_scraping_automation.sh
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "=================================================="
echo "   TrynDraft Scraping Automation Setup"
echo "=================================================="
echo ""

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT"

echo -e "${BLUE}Project root:${NC} $PROJECT_ROOT"
echo -e "${BLUE}Backend dir:${NC} $BACKEND_DIR"
echo ""

# Create logs directory
mkdir -p "$PROJECT_ROOT/../logs"

# Determine cron command based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${BLUE}Detected macOS${NC}"
    CRON_CMD="crontab"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "${BLUE}Detected Linux${NC}"
    CRON_CMD="crontab"
else
    echo -e "${YELLOW}Warning: Unsupported OS. Manual setup required.${NC}"
    CRON_CMD="crontab"
fi

# Create wrapper script for cron
WRAPPER_SCRIPT="$BACKEND_DIR/scripts/cron_scrape_wrapper.sh"

cat > "$WRAPPER_SCRIPT" << 'EOF'
#!/bin/bash
# Wrapper script for cron jobs to ensure correct environment

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"

# Load environment
if [ -f "$BACKEND_DIR/.env" ]; then
    export $(cat "$BACKEND_DIR/.env" | grep -v '^#' | xargs)
fi

# Activate virtual environment
if [ -f "$BACKEND_DIR/.venv/bin/activate" ]; then
    source "$BACKEND_DIR/.venv/bin/activate"
fi

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# Run the scraper
cd "$BACKEND_DIR"
python scripts/run_scrapers.py "$@" >> "$PROJECT_ROOT/logs/cron_scraping.log" 2>&1

# Log completion
echo "[$(date)] Scraping job completed: $@" >> "$PROJECT_ROOT/logs/cron_scraping.log"
EOF

chmod +x "$WRAPPER_SCRIPT"
echo -e "${GREEN}✓${NC} Created wrapper script: $WRAPPER_SCRIPT"

# Create cron jobs
echo ""
echo "Creating cron jobs..."
echo ""

# Backup existing crontab
$CRON_CMD -l > /tmp/crontab_backup_tryndraft_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Create new cron entries
CRON_ENTRIES=$(cat << CRONEOF
# TrynDraft Automated Scraping
# Stats scraping: Every day at 3 AM (scrape Gold rank - most popular)
0 3 * * * $WRAPPER_SCRIPT stats --rank GOLD

# Stats scraping: Every Monday at 4 AM (scrape high elo)
0 4 * * 1 $WRAPPER_SCRIPT stats --mode high_elo

# LLM text scraping: Every Sunday at 2 AM
0 2 * * 0 $WRAPPER_SCRIPT text

# Load scraped data: Every day at 5 AM
0 5 * * * $WRAPPER_SCRIPT load

# Status check: Every day at 6 AM (log current status)
0 6 * * * $WRAPPER_SCRIPT status >> $PROJECT_ROOT/logs/scraping_status.log 2>&1
CRONEOF
)

echo "$CRON_ENTRIES" | $CRON_CMD -

echo -e "${GREEN}✓${NC} Cron jobs installed"
echo ""

echo "=================================================="
echo "   Automation Setup Complete!"
echo "=================================================="
echo ""
echo "Scheduled jobs:"
echo "  Daily at 3 AM:    Scrape GOLD rank stats"
echo "  Weekly Monday:    Scrape high elo stats"
echo "  Weekly Sunday:    Scrape LLM training data"
echo "  Daily at 5 AM:    Load scraped stats into DB"
echo "  Daily at 6 AM:    Log status"
echo ""
echo "Logs:"
echo "  Scraping logs: $PROJECT_ROOT/logs/cron_scraping.log"
echo "  Status logs:   $PROJECT_ROOT/logs/scraping_status.log"
echo ""
echo "To view current cron jobs:"
echo "  crontab -l"
echo ""
echo "To remove automation:"
echo "  ./scripts/remove_scraping_automation.sh"
echo ""
echo "To run scraper manually:"
echo "  cd $BACKEND_DIR"
echo "  source .venv/bin/activate"
echo "  python scripts/run_scrapers.py stats --mode quick"
echo ""
