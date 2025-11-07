#!/bin/bash

# Start both backend and frontend servers

echo "🚀 Starting Video Shorts Generator..."
echo ""

# Start backend API server in the background
echo "📡 Starting backend API server on http://localhost:8000..."
python main.py &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 3

# Start frontend dev server
echo "🎨 Starting frontend dev server on http://0.0.0.0:5000..."
cd frontend && npm run dev

# When frontend exits, kill backend too
kill $BACKEND_PID
