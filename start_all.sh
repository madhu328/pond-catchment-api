#!/bin/bash
DIR="/home/student/pond_catchment"
cd "$DIR"

chmod +x "$DIR/run_backend_daemon.sh" "$DIR/run_frontend_daemon.sh"

# Stop previous processes
pkill -9 -f "run_backend_daemon.sh" 2>/dev/null || true
pkill -9 -f "run_frontend_daemon.sh" 2>/dev/null || true
pkill -9 -f "run_backend.py" 2>/dev/null || true
pkill -9 -f "serve_frontend.py" 2>/dev/null || true
fuser -k -9 3000/tcp 2>/dev/null || true
fuser -k -9 4000/tcp 2>/dev/null || true
sleep 1

# Start daemons fully detached
(nohup bash "$DIR/run_backend_daemon.sh" >/dev/null 2>&1 < /dev/null &)
(nohup bash "$DIR/run_frontend_daemon.sh" >/dev/null 2>&1 < /dev/null &)

sleep 3

echo "=== DAEMON PROCESSES ==="
ps aux | grep -E "run_backend|serve_frontend" | grep -v grep || true

echo "=== LISTENING PORTS ==="
ss -tlpn | grep -E "3000|4000" || true

echo "=== SUCCESS_LAUNCH ==="
