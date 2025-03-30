#!/bin/bash

# Check if running on Windows
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows (Git Bash or similar)
    PYTHON="python"
else
    # Linux/Mac
    PYTHON="python3"
fi

# Create directories
mkdir -p uploads
mkdir -p processed
mkdir -p chroma_db

# Function to handle cleanup on exit
cleanup() {
    echo "Stopping services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Register the cleanup function for signals
trap cleanup SIGINT SIGTERM

# Start FastAPI backend
echo "Starting FastAPI backend..."
$PYTHON -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Start Streamlit frontend
echo "Starting Streamlit frontend..."
$PYTHON -m streamlit run app/frontend/main.py --server.port 8501 --server.address 0.0.0.0 &
FRONTEND_PID=$!

echo "Services started:"
echo "FastAPI backend:  http://localhost:8000"
echo "Streamlit frontend: http://localhost:8501"
echo "Press Ctrl+C to stop both services."

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID 