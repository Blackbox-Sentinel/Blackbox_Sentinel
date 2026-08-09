"""
BlackBox Sentinel — Tactical Web OS Server
Serves the 800x480 Tactical Touchscreen OS for Ubuntu/Debian/Pi Kiosk mode & Remote Command
"""

import os
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Ensure stdout handles UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PORT = 8080
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


class SentinelHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        # Clean logging
        pass


def run_server(open_browser=False):
    server = HTTPServer(("0.0.0.0", PORT), SentinelHTTPHandler)
    url = f"http://localhost:{PORT}"
    print("=" * 65)
    print("  [SENTINEL-OS] Tactical Touchscreen Web OS Server")
    print(f"  URL: {url}")
    print(f"  Serving directory: {WEB_DIR}")
    print("=" * 65)
    
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Sentinel OS Server...")
        server.server_close()


if __name__ == "__main__":
    run_server(open_browser=False)
