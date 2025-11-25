#!/bin/bash
# TuxSec Logs Script
# View logs from running services

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

show_usage() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}TuxSec Logs Viewer${NC}"
    echo -e "${BLUE}================================${NC}"
    echo
    echo "Usage: $0 [sync|web|api] [lines]"
    echo
    echo "Services:"
    echo "  sync  - View Sync Agents Scheduler logs"
    echo "  web   - View Django Web UI logs (not yet implemented)"
    echo "  api   - View API Server logs (not yet implemented)"
    echo
    echo "Options:"
    echo "  lines - Number of lines to show (default: follow mode with -f)"
    echo
    echo "Examples:"
    echo "  $0 sync         # Follow sync logs in real-time"
    echo "  $0 sync 100     # Show last 100 lines of sync logs"
    echo
}

if [ $# -eq 0 ]; then
    show_usage
    exit 0
fi

SERVICE="$1"
LINES="${2:-}"

case "$SERVICE" in
    sync)
        LOG_FILE="${SCRIPT_DIR}/web_ui/logs/sync.log"
        if [ ! -f "$LOG_FILE" ]; then
            echo -e "${RED}✗ Sync log file not found: $LOG_FILE${NC}"
            echo -e "${YELLOW}  Make sure the Sync Agents Scheduler is running${NC}"
            exit 1
        fi
        
        echo -e "${BLUE}Viewing Sync Agents Scheduler logs${NC}"
        echo -e "${BLUE}Log file: ${LOG_FILE}${NC}"
        echo -e "${BLUE}================================${NC}"
        echo
        
        if [ -z "$LINES" ]; then
            tail -f "$LOG_FILE"
        else
            tail -n "$LINES" "$LOG_FILE"
        fi
        ;;
    
    web)
        echo -e "${YELLOW}⚠ Django Web UI logs not yet configured${NC}"
        echo -e "${YELLOW}  Check the terminal where you started the web UI${NC}"
        exit 1
        ;;
    
    api)
        echo -e "${YELLOW}⚠ API Server logs not yet configured${NC}"
        echo -e "${YELLOW}  Check the terminal where you started the API server${NC}"
        exit 1
        ;;
    
    *)
        echo -e "${RED}✗ Unknown service: $SERVICE${NC}"
        echo
        show_usage
        exit 1
        ;;
esac
