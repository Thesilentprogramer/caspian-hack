from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from privacy_guard_agent.stats import Stats

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
_PAGE = Path(__file__).with_name("dashboard.html")


def start_dashboard(
    stats: Stats,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> ThreadingHTTPServer:
    handler = _handler_for(stats)
    server = ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(
        target=server.serve_forever,
        name="privacy-guard-dashboard",
        daemon=True,
    )
    thread.start()
    return server


def _handler_for(stats: Stats) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path.split("?", 1)[0] == "/stats.json":
                body = json.dumps(stats.snapshot()).encode()
                self._send(200, "application/json; charset=utf-8", body)
                return
            if self.path.split("?", 1)[0] in {"/", "/index.html"}:
                self._send(200, "text/html; charset=utf-8", _PAGE.read_bytes())
                return
            self._send(404, "text/plain; charset=utf-8", b"not found")

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return DashboardHandler
