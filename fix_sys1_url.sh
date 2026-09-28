#!/bin/bash
# --------------------------------------------------------------------------
# fix_sys1_url.sh
# Fixes and ensures http://10.1.75.51:3313/ is accessible for your professor
# --------------------------------------------------------------------------

echo "=================================================================="
echo "  JALDRISHTI 24/7 SERVER DIAGNOSTIC & FIX FOR http://10.1.75.51:3313"
echo "=================================================================="

PORT=3313
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# 1. Kill any existing server process on port 3313
PID=$(pgrep -f "run_server.py $PORT")
if [ -n "$PID" ]; then
    echo "Stopping old server process PID $PID..."
    kill -9 $PID 2>/dev/null
fi

# 2. Start server bound explicitly to 0.0.0.0 on port 3313
echo "Starting FastAPI server on 0.0.0.0:$PORT..."
if [ -f "./venv/bin/python" ]; then
    nohup ./venv/bin/python run_server.py $PORT > server.log 2>&1 &
else
    nohup python3 run_server.py $PORT > server.log 2>&1 &
fi

SERVER_PID=$!
sleep 2

# 3. Verify server responds on localhost
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/)
if [ "$RESPONSE" == "200" ]; then
    echo "✅ Local server is RUNNING and returning HTTP 200 OK!"
else
    echo "⚠️ Server status: $RESPONSE (checking server.log...)"
    cat server.log | tail -n 10
fi

# 4. Attempt SSH Reverse Port Forward to host gateway 172.17.0.1 / 10.1.75.51
echo "Establishing reverse port forward to host gateway 172.17.0.1..."
nohup ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -R 0.0.0.0:3313:127.0.0.1:3313 student@172.17.0.1 > gateway_tunnel.log 2>&1 &

echo "------------------------------------------------------------------"
echo "Server process PID: $SERVER_PID"
echo "URL for Professor: http://10.1.75.51:3313/"
echo "=================================================================="
