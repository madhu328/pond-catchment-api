#!/bin/bash
DIR="/home/student/pond_catchment/frontend"
cd "$DIR"

if [ -f "/home/student/pond_backend/venv/bin/python" ]; then
    PYTHON_BIN="/home/student/pond_backend/venv/bin/python"
elif [ -f "$DIR/venv/bin/python" ]; then
    PYTHON_BIN="$DIR/venv/bin/python"
else
    PYTHON_BIN="python3"
fi

fuser -k -9 3000/tcp 2>/dev/null || true
pkill -9 -f "serve_frontend.py 3000" 2>/dev/null || true
sleep 1

while true; do
    echo "[$(date)] Starting Frontend Server using $PYTHON_BIN on port 3000..." >> "$DIR/frontend.log"
    "$PYTHON_BIN" -u serve_frontend.py 3000 http://127.0.0.1:4000 >> "$DIR/frontend.log" 2>&1
    echo "[$(date)] Frontend stopped. Restarting in 2s..." >> "$DIR/frontend.log"
    sleep 2
done
