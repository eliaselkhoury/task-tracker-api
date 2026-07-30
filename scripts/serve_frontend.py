"""Serve the frontend for local development, without browser caching.

Why this exists instead of `python -m http.server --directory frontend`:

`http.server` sends `Last-Modified` but no `Cache-Control` and no `ETag`. With no
explicit freshness information, browsers fall back to *heuristic* caching
(RFC 9111 section 4.2.2) and will happily serve a cached styles.css or app.js
without revalidating. The practical result is that you edit a file, reload, and
see the old page - which looks exactly like your fix not working. That cost real
debugging time on this project: a CSS fix was already correct and already being
served, while the browser kept showing the broken version.

VS Code's Live Server extension does not have this problem, so if you use that
(as the course videos do) you do not need this script.

Usage:
    python scripts/serve_frontend.py           # http://127.0.0.1:5500
    python scripts/serve_frontend.py 8080      # a different port
"""

import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
DEFAULT_PORT = 5500
HOST = "127.0.0.1"


class NoCacheHandler(SimpleHTTPRequestHandler):
    """A static file handler that tells the browser never to cache."""

    def end_headers(self) -> None:
        # no-store is the blunt instrument, and blunt is right for a dev server:
        # every reload must reflect what is on disk.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:
        # Keep the default logging, just prefixed so it is obvious which server
        # a line came from when the API is running in another terminal.
        sys.stderr.write(f"[frontend] {self.address_string()} - {format % args}\n")


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT

    if not FRONTEND_DIR.is_dir():
        raise SystemExit(f"frontend directory not found: {FRONTEND_DIR}")

    handler = partial(NoCacheHandler, directory=str(FRONTEND_DIR))
    with ThreadingHTTPServer((HOST, port), handler) as server:
        print(f"Serving {FRONTEND_DIR} at http://{HOST}:{port} (caching disabled)")
        print("Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
