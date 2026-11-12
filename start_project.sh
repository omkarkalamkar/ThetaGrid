#!/bin/bash

# Color codes for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting ThetaGrid Project...${NC}"
echo "================================"

# Function to check if a port is in use
check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${YELLOW}Port $port is already in use ($service)${NC}"
        return 1
    fi
    return 0
}

# Kill any existing processes on these ports
echo "Cleaning up existing processes on ports 8000 and 5173..."
pkill -f "uvicorn.*8000" 2>/dev/null
pkill -f "npm.*dev" 2>/dev/null

# Check if ports are free
check_port 8000 "Backend" || exit 1
check_port 5173 "Frontend" || exit 1

# Start backend
echo -e "\n${GREEN}Starting Backend (FastAPI) on http://localhost:8000${NC}"
echo "------------------------"
cd /Users/omkar/Documents/ThetaGrid/backend

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}Virtual environment not found!${NC}"
    echo "Please create it with: python -m venv .venv"
    echo "And install requirements: pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment and start backend
source .venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Give backend a moment to start
sleep 5

# Start frontend
echo -e "\n${GREEN}Starting Frontend (React/Vite) on http://localhost:5173${NC}"
echo "------------------------"
cd /Users/omkar/Documents/ThetaGrid/frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}node_modules not found! Installing dependencies...${NC}"
    npm install
fi

npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

# Wait a moment for services to start
sleep 3

echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}ThetaGrid is now running!${NC}"
echo -e "${GREEN}================================${NC}"
echo -e "Frontend: ${YELLOW}http://localhost:5173/${NC}"
echo -e "Backend API: ${YELLOW}http://localhost:8000/${NC}"
echo -e "API Documentation: ${YELLOW}http://localhost:8000/docs${NC}"
echo -e "\nPress Ctrl+C to stop both services"

# Trap Ctrl+C to clean up
trap 'echo -e "\n${RED}Stopping services...${NC}"; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0' INT

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID