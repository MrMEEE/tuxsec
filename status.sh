#!/bin/bash
# TuxSec Status Script
# Check status of API Server, Web UI, and Sync Agents Scheduler

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}TuxSec Status${NC}"
echo -e "${BLUE}================================${NC}"
echo

# Check API Server
if lsof -i :8000 > /dev/null 2>&1; then
    pid=$(lsof -ti :8000)
    echo -e "${GREEN}✓ API Server:           Running${NC} (PID: $pid, Port: 8000)"
else
    echo -e "${RED}✗ API Server:           Not running${NC}"
fi

# Check Django Web UI
if lsof -i :8001 > /dev/null 2>&1; then
    pid=$(lsof -ti :8001)
    echo -e "${GREEN}✓ Django Web UI:        Running${NC} (PID: $pid, Port: 8001)"
else
    echo -e "${RED}✗ Django Web UI:        Not running${NC}"
fi

# Check Sync Agents Scheduler
if pgrep -f "sync_agents --daemon" > /dev/null 2>&1; then
    pid=$(pgrep -f "sync_agents --daemon")
    echo -e "${GREEN}✓ Sync Agents Scheduler: Running${NC} (PID: $pid)"
else
    echo -e "${RED}✗ Sync Agents Scheduler: Not running${NC}"
fi

echo
echo -e "${BLUE}================================${NC}"
