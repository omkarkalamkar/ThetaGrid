#!/bin/bash
echo "Starting ThetaGrid..."
echo ""

# Start backend
echo "Starting backend on http://localhost:8000"
cd /Users/omkar/Documents/ThetaGrid/backend
source .venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend
sleep 5

# Start frontend
echo ""
echo "Starting frontend on http://localhost:5173"
cd /Users/omkar/Documents/ThetaGrid/frontend
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

# Wait for frontend
sleep 3

echo ""
echo "========================================"
echo "ThetaGrid is running!"
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000"
echo "Docs:     http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both services"
echo "========================================"

# Cleanup on exit
trap 'echo ""; echo "Stopping services..."; kill $BACKEND_PID $FRONTEND_PID; exit 0' INT

# Wait for user to press Ctrl+C
wait