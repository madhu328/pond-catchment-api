#!/bin/bash
DIR="/home/student/pond_catchment/backend"
cd "$DIR"

# Select Python binary with all dependencies
if [ -f "/home/student/pond_backend/venv/bin/python" ]; then
    PYTHON_BIN="/home/student/pond_backend/venv/bin/python"
elif [ -f "$DIR/venv/bin/python" ]; then
    PYTHON_BIN="$DIR/venv/bin/python"
else
    PYTHON_BIN="python3"
fi

fuser -k -9 4000/tcp 2>/dev/null || true
pkill -9 -f "run_backend.py 4000" 2>/dev/null || true
sleep 1

while true; do
    echo "[$(date)] Starting Backend API using $PYTHON_BIN on port 4000..." >> "$DIR/backend.log"
    "$PYTHON_BIN" -u run_backend.py 4000 >> "$DIR/backend.log" 2>&1
    echo "[$(date)] Backend stopped. Restarting in 2s..." >> "$DIR/backend.log"
    sleep 2
done
