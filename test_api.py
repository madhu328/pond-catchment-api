"""
test_api.py
-----------
Quick manual test / demo script.
Make sure the server is running first:
    uvicorn app.main:app --reload

Then run:
    python test_api.py path/to/contours_1m.kml
"""

import os
import sys
import json
import requests

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_api.py <path_to_kml_or_kmz> [port_or_url]")
        sys.exit(1)

    file_path = sys.argv[1]
    url = "http://127.0.0.1:3313/analyzeContour"
    if len(sys.argv) > 2:
        arg = sys.argv[2]
        if arg.isdigit():
            url = f"http://127.0.0.1:{arg}/analyzeContour"
        else:
            url = arg
    file_name = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        files = {"contour_map": (file_name, f, "application/vnd.google-earth.kml+xml")}
        response = requests.post(url, files=files)

    print("Status code:", response.status_code)
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
