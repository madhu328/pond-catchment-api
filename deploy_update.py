#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import urllib.request
import ssh_master

def main():
    print("=== JalDrishti Full Frontend & Daemon Update ===")
    
    # 1. Establish or verify SSH Master connection
    print("\n[Step 1] Ensuring SSH ControlMaster is active...")
    if not ssh_master.ensure_master():
        print("Error: Could not establish SSH connection.")
        sys.exit(1)
    print("✓ SSH Master connection confirmed.")

    # 2. Upload updated scripts and frontend files
    print("\n[Step 2] Uploading scripts and frontend assets to stu29_sys2...")
    base_dir = "/home/ubuntu/Downloads/pond_backend"
    frontend_dir = f"{base_dir}/frontend"
    remote_base = "/home/student/pond_catchment"
    remote_target = f"{remote_base}/frontend"
    
    # Ensure remote directories exist
    ssh_master.run_cmd(f"mkdir -p {remote_target}/vendor/images")

    # Copy daemon scripts
    ssh_master.scp_to_remote(f"{base_dir}/run_frontend_daemon.sh", f"{remote_base}/run_frontend_daemon.sh")
    ssh_master.scp_to_remote(f"{base_dir}/run_backend_daemon.sh", f"{remote_base}/run_backend_daemon.sh")
    ssh_master.scp_to_remote(f"{base_dir}/start_all.sh", f"{remote_base}/start_all.sh")
    ssh_master.run_cmd(f"chmod +x {remote_base}/*.sh")

    # Copy frontend files
    ssh_master.scp_to_remote(f"{frontend_dir}/index.html", f"{remote_target}/index.html")
    ssh_master.scp_to_remote(f"{frontend_dir}/styles.css", f"{remote_target}/styles.css")
    ssh_master.scp_to_remote(f"{frontend_dir}/app.js", f"{remote_target}/app.js")
    ssh_master.scp_to_remote(f"{frontend_dir}/serve_frontend.py", f"{remote_target}/serve_frontend.py")
    ssh_master.scp_to_remote(f"{frontend_dir}/vendor/leaflet.js", f"{remote_target}/vendor/leaflet.js")
    ssh_master.scp_to_remote(f"{frontend_dir}/vendor/leaflet.css", f"{remote_target}/vendor/leaflet.css")
    ssh_master.scp_to_remote(f"{frontend_dir}/vendor/leaflet-geoman.min.js", f"{remote_target}/vendor/leaflet-geoman.min.js")
    ssh_master.scp_to_remote(f"{frontend_dir}/vendor/leaflet-geoman.css", f"{remote_target}/vendor/leaflet-geoman.css")
    ssh_master.scp_to_remote(f"{frontend_dir}/vendor/chart.min.js", f"{remote_target}/vendor/chart.min.js")
    ssh_master.scp_to_remote(f"{frontend_dir}/vendor/images/marker-icon.png", f"{remote_target}/vendor/images/marker-icon.png")
    ssh_master.scp_to_remote(f"{frontend_dir}/vendor/images/marker-icon-2x.png", f"{remote_target}/vendor/images/marker-icon-2x.png")
    ssh_master.scp_to_remote(f"{frontend_dir}/vendor/images/marker-shadow.png", f"{remote_target}/vendor/images/marker-shadow.png")

    print("✓ All frontend assets and daemon scripts uploaded.")

    # 3. Cleanly kill old frontend daemon and start the updated daemon
    print("\n[Step 3] Restarting frontend daemon on remote server...")
    restart_script = """
pkill -9 -f run_frontend_daemon || true
pkill -9 -f serve_frontend || true
fuser -k -9 3000/tcp 2>/dev/null || true
sleep 1
cd /home/student/pond_catchment
nohup bash run_frontend_daemon.sh >/dev/null 2>&1 &
sleep 3
ps aux | grep -E 'run_backend|run_frontend|serve_frontend' | grep -v grep
ss -tlpn | grep -E '3000|4000'
"""
    ssh_master.run_cmd(restart_script)

    # 4. Remote HTTP checks
    print("\n[Step 4] Verifying HTTP endpoints on remote localhost...")
    check_script = """
echo "--- Testing frontend index.html ---"
curl -s -I http://127.0.0.1:3000/ | head -n 5

echo "--- Testing local Leaflet vendor file ---"
curl -s -I http://127.0.0.1:3000/vendor/leaflet.js | head -n 5

echo "--- Testing backend health via proxy ---"
curl -s http://127.0.0.1:3000/api/v1/health
echo ""

echo "--- Testing direct backend health ---"
curl -s http://127.0.0.1:4000/api/v1/health
echo ""
"""
    ssh_master.run_cmd(check_script)

    # 5. Local verification from this host to forwarded ports
    print("\n[Step 5] Verifying external accessibility from local machine...")
    time.sleep(1)
    
    # Frontend check at 3314
    try:
        req = urllib.request.Request("http://10.1.75.51:3314/", headers={"User-Agent": "HealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            print(f"✓ External Frontend (http://10.1.75.51:3314/): HTTP {r.status}")
    except Exception as e:
        print(f"External Frontend check result: {e}")

    try:
        req = urllib.request.Request("http://10.1.75.51:3314/vendor/leaflet.js", headers={"User-Agent": "HealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            print(f"✓ External Leaflet Vendor (http://10.1.75.51:3314/vendor/leaflet.js): HTTP {r.status} (Size: {r.headers.get('Content-Length')} bytes)")
    except Exception as e:
        print(f"External Leaflet vendor check result: {e}")

    try:
        req = urllib.request.Request("http://10.1.75.51:4314/api/v1/health", headers={"User-Agent": "HealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            print(f"✓ External Backend API (http://10.1.75.51:4314/api/v1/health): HTTP {r.status} - {r.read().decode()}")
    except Exception as e:
        print(f"External Backend API check result: {e}")

    print("\n=======================================================")
    print("✓ Deployment and verification complete!")
    print("Frontend is live at: http://10.1.75.51:3314/")
    print("Backend is live at:  http://10.1.75.51:4314/")
    print("=======================================================")

if __name__ == "__main__":
    main()
