#!/bin/bash
# TuxSec Start Script
# Starts API Server, Web UI, and Sync Agents Scheduler

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}TuxSec Startup Script${NC}"
echo -e "${BLUE}================================${NC}"
echo

# Check if virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}Error: Virtual environment not found at ${VENV_PYTHON}${NC}"
    echo "Please run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Function to check if a process is running
is_running() {
    pgrep -f "$1" > /dev/null 2>&1
}

# Function to check if API server is running (check port)
is_api_running() {
    lsof -i :8000 > /dev/null 2>&1
}

# Function to check if web UI is running (check port)
is_webui_running() {
    lsof -i :8001 > /dev/null 2>&1
}

# Function to start a component
start_component() {
    local name="$1"
    local check_pattern="$2"
    local start_command="$3"
    local wait_time="${4:-2}"
    
    if is_running "$check_pattern"; then
        echo -e "${YELLOW}⚠ ${name} is already running${NC}"
    else
        echo -e "${GREEN}▶ Starting ${name}...${NC}"
        nohup bash -c "$start_command" > /dev/null 2>&1 &
        sleep "$wait_time"
        if is_running "$check_pattern"; then
            echo -e "${GREEN}✓ ${name} started successfully${NC}"
        else
            echo -e "${RED}✗ Failed to start ${name}${NC}"
        fi
    fi
}

# Start API Server
if is_api_running; then
    echo -e "${YELLOW}⚠ API Server is already running${NC}"
else
    echo -e "${GREEN}▶ Starting API Server...${NC}"
    nohup bash -c "cd ${SCRIPT_DIR}/api_server && ${VENV_PYTHON} main.py" > /dev/null 2>&1 &
    sleep 3
    if is_api_running; then
        echo -e "${GREEN}✓ API Server started successfully${NC}"
    else
        echo -e "${RED}✗ Failed to start API Server${NC}"
    fi
fi

# Start Django Web UI
if is_webui_running; then
    echo -e "${YELLOW}⚠ Django Web UI is already running${NC}"
else
    echo -e "${GREEN}▶ Starting Django Web UI...${NC}"
    nohup bash -c "cd ${SCRIPT_DIR}/web_ui && ${VENV_PYTHON} manage.py runserver 127.0.0.1:8001" > /dev/null 2>&1 &
    sleep 3
    if is_webui_running; then
        echo -e "${GREEN}✓ Django Web UI started successfully${NC}"
    else
        echo -e "${RED}✗ Failed to start Django Web UI${NC}"
    fi
fi

# Start Sync Agents Scheduler with logging
if is_running "sync_agents --daemon"; then
    echo -e "${YELLOW}⚠ Sync Agents Scheduler is already running${NC}"
else
    echo -e "${GREEN}▶ Starting Sync Agents Scheduler...${NC}"
    mkdir -p "${SCRIPT_DIR}/web_ui/logs"
    nohup bash -c "cd ${SCRIPT_DIR}/web_ui && ${VENV_PYTHON} -u manage.py sync_agents --daemon --interval 5 2>&1 | tee logs/sync.log" > /dev/null 2>&1 &
    sleep 2
    if is_running "sync_agents --daemon"; then
        echo -e "${GREEN}✓ Sync Agents Scheduler started successfully${NC}"
        echo -e "${BLUE}  Log file: web_ui/logs/sync.log${NC}"
    else
        echo -e "${RED}✗ Failed to start Sync Agents Scheduler${NC}"
    fi
fi

echo
echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}All components started!${NC}"
echo
echo -e "${BLUE}Access points:${NC}"
echo -e "  • Web UI:     ${GREEN}http://127.0.0.1:8001${NC}"
echo -e "  • API Server: ${GREEN}http://127.0.0.1:8000${NC}"
echo
echo -e "${BLUE}To stop all components, run:${NC}"
echo -e "  ${YELLOW}./stop.sh${NC}"
echo -e "${BLUE}================================${NC}"
