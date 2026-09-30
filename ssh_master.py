import subprocess
import time
import os

HOST = "10.1.75.51"
PORT = 2314
USER = "student"
KEY = "/home/ubuntu/.ssh/id_ed25519"
SOCKET = "/tmp/ssh_mux_stu29"

def ensure_master():
    if os.path.exists(SOCKET):
        # Check if master is active
        check = subprocess.run([
            "ssh", "-O", "check", "-S", SOCKET, f"{USER}@{HOST}"
        ], capture_output=True, text=True)
        if check.returncode == 0:
            print("SSH ControlMaster already active.")
            return True

    print("Establishing SSH ControlMaster connection...", flush=True)
    for attempt in range(1, 4):
        print(f"Waiting 18s cooldown (attempt {attempt})...", flush=True)
        time.sleep(18)
        cmd = [
            "ssh",
            "-M", "-S", SOCKET,
            "-fN",
            "-o", "ControlPersist=15m",
            "-o", "IPQoS=none",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=15",
            "-i", KEY,
            "-p", str(PORT),
            f"{USER}@{HOST}"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print("✓ SSH ControlMaster established successfully!", flush=True)
            return True
        print(f"Attempt {attempt} failed: {res.stderr.strip()}", flush=True)
    return False

def run_cmd(remote_command):
    if not ensure_master():
        print("Failed to establish master.")
        return 1
    
    cmd = [
        "ssh", "-S", SOCKET, f"{USER}@{HOST}", remote_command
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print("STDOUT:")
    print(res.stdout)
    if res.stderr:
        print("STDERR:")
        print(res.stderr)
    return res.returncode

if __name__ == "__main__":
    import sys
    cmd_to_run = sys.argv[1] if len(sys.argv) > 1 else (
        "/home/student/pond_backend/venv/bin/python -m uvicorn --version 2>&1; "
        "find /home/student -name uvicorn 2>/dev/null; "
        "which uvicorn 2>&1"
    )
    sys.exit(run_cmd(cmd_to_run))
