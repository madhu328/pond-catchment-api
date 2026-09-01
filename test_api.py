"""
test_api.py
-----------
Quick manual test / demo script.
Make sure the server is running first:
    uvicorn app.main:app --reload

Then run:
    python test_api.py path/to/contours_1m.kml
"""

import sys
import json
import requests

API_URL = "http://127.0.0.1:8000/analyzeContour"


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_api.py <path_to_kml_or_kmz>")
        sys.exit(1)

    file_path = sys.argv[1]
    with open(file_path, "rb") as f:
        files = {"file": (file_path, f)}
        response = requests.post(API_URL, files=files)

    print("Status code:", response.status_code)
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
