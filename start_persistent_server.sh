#!/bin/bash
# --------------------------------------------------------------------------
# start_persistent_server.sh
# Ensures JalDrishti Village Pond Backend & Front-End runs 24/7 on port 3313
# --------------------------------------------------------------------------

PORT=${1:-3313}
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd "$DIR"

# Stop any existing server on port $PORT
PID=$(pgrep -f "run_server.py $PORT")
if [ -n "$PID" ]; then
    echo "Stopping existing server PID $PID..."
    kill -9 $PID 2>/dev/null
fi

echo "Starting 24/7 persistent JalDrishti server on port $PORT..."
nohup ./venv/bin/python run_server.py $PORT > server.log 2>&1 &

NEW_PID=$!
echo "Server started successfully in background with PID $NEW_PID."
echo "Logs are being written to $DIR/server.log"
echo "Application URL: http://0.0.0.0:$PORT"
