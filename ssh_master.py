import subprocess
import time
import os
import sys

HOST = "10.1.75.51"
PORT = 2314
USER = "student"
KEY = "/home/ubuntu/Downloads/pond_backend/.ssh_key"
SOCKET = "/tmp/ssh_mux_stu29"

def ensure_master():
    if os.path.exists(SOCKET):
        check = subprocess.run([
            "ssh", "-F", "/dev/null", "-O", "check", "-S", SOCKET, f"{USER}@{HOST}"
        ], capture_output=True, text=True)
        if check.returncode == 0:
            return True
        else:
            try:
                os.remove(SOCKET)
            except Exception:
                pass

    print("Establishing SSH ControlMaster connection...", flush=True)
    for attempt in range(1, 6):
        print(f"Waiting 16s cooldown (attempt {attempt})...", flush=True)
        time.sleep(16)
        cmd = [
            "ssh",
            "-F", "/dev/null",
            "-M", "-S", SOCKET,
            "-fN",
            "-o", "ControlPersist=30m",
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
        "ssh", "-F", "/dev/null", "-S", SOCKET, f"{USER}@{HOST}", remote_command
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    print("STDOUT:")
    print(res.stdout)
    if res.stderr:
        print("STDERR:")
        print(res.stderr)
    return res.returncode

def scp_to_remote(local_path, remote_path):
    if not ensure_master():
        print("Failed to establish master.")
        return 1
    cmd = [
        "scp", "-F", "/dev/null", "-o", f"ControlPath={SOCKET}",
        "-r", local_path, f"{USER}@{HOST}:{remote_path}"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if res.returncode == 0:
        print(f"✓ Copied {local_path} -> {remote_path}")
        return 0
    else:
        print(f"Failed to copy {local_path}: {res.stderr}")
        return res.returncode

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "check"
    if action == "check":
        sys.exit(run_cmd("whoami && uptime && ps aux | grep -E 'run_backend|serve_frontend' | grep -v grep"))
    elif action == "cmd":
        sys.exit(run_cmd(" ".join(sys.argv[2:])))
