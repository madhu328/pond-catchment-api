#!/usr/bin/env python3
"""
run_server.py
-------------
Helper script to start the FastAPI server on host 0.0.0.0 and the specified port.
Default port is 3313 (3000 + 313 for system 2313).

Usage:
    python run_server.py
    python run_server.py 3313
    python run_server.py 3314
"""

import sys
import uvicorn

def main():
    port = 3313
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port '{sys.argv[1]}', using default 3313.")

    print(f"Starting server on 0.0.0.0:{port}...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
