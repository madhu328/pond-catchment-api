import urllib.request
import json
import sys

print("=== JALDRISHTI LOCAL INTEGRATION VERIFICATION ===")

print("\n[1] Testing Frontend Web Interface on http://10.1.75.51:3314/ ...")
try:
    with urllib.request.urlopen("http://10.1.75.51:3314/", timeout=8) as r:
        html = r.read().decode("utf-8", errors="ignore")
        if r.status == 200 and "JalDrishti" in html:
            print("  ✓ SUCCESS: Frontend Web UI is accessible on port 3314 (HTTP 200 OK)")
            print(f"    Title and assets present (Page size: {len(html)} bytes)")
        else:
            print(f"  ❌ FAILED: Status {r.status}")
except Exception as e:
    print(f"  ❌ FAILED: {e}")

print("\n[2] Testing Backend API on http://10.1.75.51:4314/api/v1/health ...")
try:
    with urllib.request.urlopen("http://10.1.75.51:4314/api/v1/health", timeout=8) as r:
        data = r.read().decode("utf-8", errors="ignore")
        if r.status == 200:
            print(f"  ✓ SUCCESS: Backend API is online on port 4314 (HTTP 200 OK)")
            print(f"    Response: {data.strip()}")
        else:
            print(f"  ❌ FAILED: Status {r.status}")
except Exception as e:
    print(f"  ❌ FAILED: {e}")

print("\n[3] Testing Frontend-to-Backend Hydrology Analysis Integration via Proxy ...")
try:
    test_payload = json.dumps({
        "polygon_lonlat": [
            [81.2850, 21.2430],
            [81.2930, 21.2430],
            [81.2930, 21.2490],
            [81.2850, 21.2490],
            [81.2850, 21.2430]
        ],
        "rainfall_mm": 1000.0,
        "runoff_coefficient": 0.35
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://10.1.75.51:3314/analyzeSelectedArea",
        data=test_payload,
        headers={"Content-Type": "application/json", "User-Agent": "VerificationScript/1.0"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read().decode("utf-8"))
        if "recommended_pond_location" in resp:
            pond = resp["recommended_pond_location"]
            vol = resp.get("expected_water_volume", {})
            dims = resp.get("recommended_pond_dimensions", {})
            print("  ✓ SUCCESS: End-to-end Hydrology Analysis executed!")
            print(f"    Optimal Pond Site: Latitude {pond.get('latitude')}, Longitude {pond.get('longitude')}, Elevation {pond.get('elevation_m')}m")
            print(f"    Expected Water Inflow: {vol.get('expected_volume_million_liters')} Million Liters ({vol.get('expected_volume_m3'):,.0f} m³)")
            print(f"    Recommended Pond Size: {dims.get('length_m')}m x {dims.get('width_m')}m x {dims.get('depth_m')}m")
        else:
            print(f"  ⚠ Response received but unexpected format: {resp}")
except Exception as e:
    print(f"  ❌ FAILED: {e}")

print("\n=== VERIFICATION COMPLETE ===")
