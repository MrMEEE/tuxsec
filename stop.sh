#!/bin/bash
# TuxSec Stop Script
# Stops API Server, Web UI, and Sync Agents Scheduler

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}TuxSec Stop Script${NC}"
echo -e "${BLUE}================================${NC}"
echo

# Function to stop a component
stop_component() {
    local name="$1"
    local pattern="$2"
    
    if pgrep -f "$pattern" > /dev/null 2>&1; then
        echo -e "${YELLOW}◼ Stopping ${name}...${NC}"
        pkill -f "$pattern"
        sleep 1
        if pgrep -f "$pattern" > /dev/null 2>&1; then
            echo -e "${RED}✗ Failed to stop ${name} gracefully, forcing...${NC}"
            pkill -9 -f "$pattern"
        else
            echo -e "${GREEN}✓ ${name} stopped${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ ${name} is not running${NC}"
    fi
}

# Function to stop by port
stop_by_port() {
    local name="$1"
    local port="$2"
    
    local pid=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}◼ Stopping ${name}...${NC}"
        kill $pid 2>/dev/null
        sleep 1
        if lsof -ti :$port > /dev/null 2>&1; then
            echo -e "${RED}✗ Failed to stop ${name} gracefully, forcing...${NC}"
            kill -9 $pid 2>/dev/null
        else
            echo -e "${GREEN}✓ ${name} stopped${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ ${name} is not running${NC}"
    fi
}

# Stop Sync Agents Scheduler
stop_component "Sync Agents Scheduler" "sync_agents --daemon"

# Stop Django Web UI
stop_by_port "Django Web UI" 8001

# Stop API Server
stop_by_port "API Server" 8000

echo
echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}All components stopped!${NC}"
echo -e "${BLUE}================================${NC}"
