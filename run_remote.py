import subprocess
import sys
import time

HOST = "10.1.75.51"
PORT = 2314
USER = "student"
KEY = "/home/ubuntu/.ssh/id_ed25519"

def run_remote(cmd):
    max_retries = 2
    for attempt in range(1, max_retries + 1):
        wait_time = 12 if attempt == 1 else 16
        print(f"Waiting {wait_time}s for router TCP cooldown (attempt {attempt}/{max_retries})...", flush=True)
        time.sleep(wait_time)

        ssh_args = [
            "ssh",
            "-o", "IPQoS=none",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=15",
            "-i", KEY,
            "-p", str(PORT),
            f"{USER}@{HOST}",
            cmd
        ]
        try:
            res = subprocess.run(ssh_args, capture_output=True, text=True, timeout=30)
            if res.returncode == 255 and "timed out" in res.stderr:
                print(f"Connection timed out on attempt {attempt}.", flush=True)
                continue
            print("STDOUT:")
            print(res.stdout)
            if res.stderr:
                print("STDERR:")
                print(res.stderr)
            return res.returncode
        except subprocess.TimeoutExpired:
            print(f"SSH command timed out on attempt {attempt}.", flush=True)
            continue
    return 1

if __name__ == "__main__":
    remote_cmd = sys.argv[1] if len(sys.argv) > 1 else "whoami"
    sys.exit(run_remote(remote_cmd))
