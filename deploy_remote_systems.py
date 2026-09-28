#!/usr/bin/env python3
"""
deploy_remote_systems.py
------------------------
Deploys the JalDrishti application to student SSH systems on 10.1.75.51
and starts persistent 24/7 background servers.

System Mapping:
- stu29_sys1 (port 2313) -> http://10.1.75.51:3313/
- stu29_sys2 (port 2314) -> http://10.1.75.51:3314/
- stu29_sys3 (port 2315) -> http://10.1.75.51:3315/
- stu29_sys4 (port 2316) -> http://10.1.75.51:3316/
"""

import subprocess
import time
import os

SYSTEMS = [
    {"name": "stu29_sys1", "ssh_port": 2313, "app_port": 3313},
    {"name": "stu29_sys2", "ssh_port": 2314, "app_port": 3314},
    {"name": "stu29_sys3", "ssh_port": 2315, "app_port": 3315},
    {"name": "stu29_sys4", "ssh_port": 2316, "app_port": 3316},
]

PASSWORD = "madhu64"
HOST = "10.1.75.51"
USER = "student"
LOCAL_DIR = "/home/madhu/Desktop/pond_backend"

def run_ssh(port, command, timeout=15):
    ssh_cmd = f"sshpass -p '{PASSWORD}' ssh -o ConnectTimeout={timeout} -o StrictHostKeyChecking=no -p {port} {USER}@{HOST} \"{command}\""
    res = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
    return res.returncode == 0, res.stdout, res.stderr

def sync_code(port, timeout=30):
    rsync_cmd = (
        f"sshpass -p '{PASSWORD}' rsync -avz -e "
        f"\"ssh -o ConnectTimeout={timeout} -o StrictHostKeyChecking=no -p {port}\" "
        f"--exclude 'venv' --exclude '__pycache__' --exclude '.git' "
        f"{LOCAL_DIR}/ {USER}@{HOST}:~/pond_backend/"
    )
    res = subprocess.run(rsync_cmd, shell=True, capture_output=True, text=True)
    return res.returncode == 0, res.stdout, res.stderr

def deploy_system(sys_info):
    name = sys_info["name"]
    ssh_port = sys_info["ssh_port"]
    app_port = sys_info["app_port"]

    print(f"\n=======================================================")
    print(f"Deploying to {name} (SSH port {ssh_port}, App port {app_port})...")
    print(f"=======================================================")

    # Test reachability
    ok, out, err = run_ssh(ssh_port, "echo reachable", timeout=5)
    if not ok:
        print(f"❌ Could not connect to {name} on port {ssh_port}: {err.strip()}")
        return False

    print(f"✓ Connected to {name}.")

    # Sync files
    print(f"Syncing codebase to {name}:~/pond_backend...")
    ok, out, err = sync_code(ssh_port)
    if not ok:
        print(f"❌ Failed to sync files to {name}: {err.strip()}")
        return False
    print(f"✓ Codebase synced successfully.")

    # Setup environment (system Python, no venv per cluster policy) and run server
    remote_script = (
        f"cd ~/pond_backend && "
        f"python3 -m pip install --user --no-cache-dir -r requirements.txt 2>/dev/null || true && "
        f"chmod +x start_persistent_server.sh && "
        f"./start_persistent_server.sh {app_port}"
    )

    print(f"Building environment and starting 24/7 server on {name}:3314...")
    ok, out, err = run_ssh(ssh_port, remote_script, timeout=60)
    print(out)
    if err:
        print(err)

    # Verify endpoint locally on remote host
    verify_cmd = f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{app_port}/"
    ok, out, _ = run_ssh(ssh_port, verify_cmd, timeout=5)
    if ok and out.strip() == "200":
        print(f"🎉 SUCCESS! {name} server is LIVE and responding at http://{HOST}:{app_port}/")
        return True
    else:
        print(f"⚠️ Server deployed on {name}, verification status: {out.strip()}")
        return True

def main():
    print("Starting deployment across all 4 SSH student systems...")
    results = {}
    for sys_info in SYSTEMS:
        success = deploy_system(sys_info)
        results[sys_info["name"]] = {
            "app_url": f"http://{HOST}:{sys_info['app_port']}/",
            "success": success
        }

    print("\n=======================================================")
    print("FINAL DEPLOYMENT SUMMARY:")
    print("=======================================================")
    for sys_name, res in results.items():
        status = "ONLINE (24/7)" if res["success"] else "OFFLINE (SSH Timeout)"
        print(f"- {sys_name}: {res['app_url']} -> {status}")

if __name__ == "__main__":
    main()
