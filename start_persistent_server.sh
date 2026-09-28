#!/bin/bash
# --------------------------------------------------------------------------
# start_persistent_server.sh
# 24/7 Auto-restarting watchdog daemon for JalDrishti Village Pond Backend
# --------------------------------------------------------------------------

PORT=${1:-3000}
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# 1. Kill any existing process on $PORT
fuser -k -9 ${PORT}/tcp 2>/dev/null || true
pkill -9 -f "run_server.py ${PORT}" 2>/dev/null || true
pkill -9 -f "watchdog_${PORT}.sh" 2>/dev/null || true
sleep 1

# 2. Select Python binary (venv Python if available, else system Python)
if [ -f "$DIR/venv/bin/python" ]; then
    PYTHON_BIN="$DIR/venv/bin/python"
else
    PYTHON_BIN="python3"
fi

# 3. Create persistent watchdog runner script
WATCHDOG_SCRIPT="/tmp/watchdog_${PORT}.sh"
cat << EOF > "$WATCHDOG_SCRIPT"
#!/bin/bash
while true; do
    echo "[\$(date)] Starting JalDrishti server on port ${PORT}..." >> "${DIR}/server_${PORT}.log"
    ${PYTHON_BIN} "${DIR}/run_server.py" ${PORT} >> "${DIR}/server_${PORT}.log" 2>&1
    echo "[\$(date)] Server exited (code \$?). Auto-restarting in 2 seconds..." >> "${DIR}/server_${PORT}.log"
    sleep 2
done
EOF
chmod +x "$WATCHDOG_SCRIPT"

echo "Starting 24/7 watchdog server using $PYTHON_BIN on port $PORT..."
nohup "$WATCHDOG_SCRIPT" > /dev/null 2>&1 &

sleep 2

PID=$(pgrep -f "run_server.py ${PORT}" | head -n 1)
if [ -n "$PID" ]; then
    echo "✅ Server started successfully in background on port $PORT (PID $PID)."
else
    echo "⚠️ Watchdog launched for port $PORT. Inspecting log:"
    tail -n 10 "${DIR}/server_${PORT}.log"
fi

# 4. Launch localhost.run SSH tunnel
nohup ssh -n -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R 80:127.0.0.1:$PORT nokey@localhost.run < /dev/null > "${DIR}/tunnel_${PORT}.log" 2>&1 &

sleep 3

PUBLIC_URL=$(grep -o 'https://[-a-zA-Z0-9]*\.lhr\.life' "${DIR}/tunnel_${PORT}.log" | tail -n 1)
if [ -n "$PUBLIC_URL" ]; then
    echo "$PUBLIC_URL" > "${DIR}/PUBLIC_URL_${PORT}.txt"
    echo "Public URL for port $PORT: $PUBLIC_URL"
else
    echo "Local server active on http://0.0.0.0:$PORT"
fi
