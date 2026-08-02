"""
Simple HTTP server for serving the web frontend.
Uses Python's built-in http.server module.
"""

import os
import mimetypes
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread


class WebHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves files from the web/ directory."""

    web_dir = None

    def __init__(self, *args, **kwargs):
        if WebHandler.web_dir:
            super().__init__(*args, directory=WebHandler.web_dir, **kwargs)
        else:
            super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        """Suppress default HTTP request logging."""
        pass


def start_web_server(host: str = "0.0.0.0", port: int = 8080) -> HTTPServer:
    """Start the web frontend HTTP server."""
    web_dir = str(Path(__file__).parent.parent / "web")
    WebHandler.web_dir = web_dir

    server = HTTPServer((host, port), WebHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def get_web_url(host: str, port: int) -> str:
    """Get the URL to open the web frontend."""
    display_host = host if host != "0.0.0.0" else "localhost"
    return f"http://{display_host}:{port}"
