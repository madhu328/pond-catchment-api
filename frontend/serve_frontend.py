#!/usr/bin/env python3
"""
serve_frontend.py
-----------------
Lightweight frontend web server serving vanilla HTML/CSS/JS.
Runs on port 3000 by default (forwarded to port 3314 on 10.1.75.51).

Includes a built-in reverse proxy for /analyzeSelectedArea, /analyzeContour,
and /findCatchment to forward requests directly to the backend server (port 4000).
This ensures 100% reliable local browser connectivity without CORS issues.
"""

import os
import sys
import urllib.request
import urllib.error
import http.server
import socketserver

DEFAULT_PORT = 3000
DEFAULT_BACKEND = os.environ.get("BACKEND_URL", "http://127.0.0.1:4000")

PROXY_PREFIXES = (
    "/analyzeSelectedArea",
    "/analyzeContour",
    "/findCatchment",
    "/api",
    "/health",
    "/docs",
    "/openapi.json"
)

class FrontendAndProxyHandler(http.server.SimpleHTTPRequestHandler):
    backend_url = DEFAULT_BACKEND

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def _should_proxy(self):
        path = self.path.split("?")[0]
        return any(path == prefix or path.startswith(prefix + "/") for prefix in PROXY_PREFIXES)

    def _proxy_request(self, method):
        target_url = f"{self.backend_url}{self.path}"
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        headers = {}
        for key in ("Content-Type", "Accept", "User-Agent"):
            val = self.headers.get(key)
            if val:
                headers[key] = val

        req = urllib.request.Request(target_url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ("transfer-encoding", "content-encoding", "access-control-allow-origin"):
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() not in ("transfer-encoding", "content-encoding", "access-control-allow-origin"):
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as err:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            err_msg = f'{{"error": "Backend gateway error", "detail": "{str(err)}"}}'
            self.wfile.write(err_msg.encode())

    def do_GET(self):
        if self._should_proxy():
            return self._proxy_request("GET")
        if self.path in ("", "/"):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self._should_proxy():
            return self._proxy_request("POST")
        self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        # Concise logging
        print(f"[Frontend] {args[0]}")


def main():
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port '{sys.argv[1]}', using {port}.")

    backend = DEFAULT_BACKEND
    if len(sys.argv) > 2:
        backend = sys.argv[2]
    FrontendAndProxyHandler.backend_url = backend

    frontend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(frontend_dir)

    http.server.ThreadingHTTPServer.allow_reuse_address = True
    with http.server.ThreadingHTTPServer(("0.0.0.0", port), FrontendAndProxyHandler) as httpd:
        print("============================================================")
        print(f"  JalDrishti Frontend Server Running")
        print(f"  Port: 0.0.0.0:{port}")
        print(f"  Static Directory: {frontend_dir}")
        print(f"  Backend Proxy Target: {backend}")
        print("============================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down frontend server.")

if __name__ == "__main__":
    main()
