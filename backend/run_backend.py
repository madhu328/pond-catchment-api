#!/usr/bin/env python3
"""
run_backend.py
--------------
Starts the JalDrishti FastAPI backend server on host 0.0.0.0 and port 4000 (default).
"""

import sys
import uvicorn

def main():
    port = 4000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port '{sys.argv[1]}', using default {port}.")

    print(f"============================================================")
    print(f"  Starting JalDrishti Backend API server on 0.0.0.0:{port}")
    print(f"============================================================")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
