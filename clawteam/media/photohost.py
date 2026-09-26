"""Loopback photo host: the ONLY process the public tunnel may reach.

Serves exactly one thing — unexpired, token-named photo files from the
uploads store — over a dedicated loopback port. The cloudflared tunnel
for the operator's public hostname points here, never at the board
(8788), so the control-plane API keeps zero public exposure.

Run standalone:  python -m clawteam.media.photohost [--port 18790]
The board embeds the same server in a daemon thread (board up = photo
lane up; board down = no public surface at all).
"""

from __future__ import annotations

import argparse
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from clawteam.media.uploads import ALLOWED_EXT, UploadStore, photohost_config

# Public path shape: /pho-<epoch>-<hex12>.<ext> — validated via TOKEN_RE +
# the ALLOWED_EXT whitelist in uploads; nothing else is ever reachable.


class PhotoHostHandler(BaseHTTPRequestHandler):
    """GET/HEAD only; every miss is 404, every expired token is 410."""

    uploads: UploadStore = None  # injected by the server factory

    protocol_version = "HTTP/1.1"

    def do_GET(self):
        path = urlparse(self.path).path
        segment = unquote(path).lstrip("/")
        if "/" in segment or ".." in segment or "\\" in segment:
            self._deny(400, "bad request")
            return
        token, dot, ext = segment.rpartition(".")
        if not dot or f".{ext.lower()}" not in ALLOWED_EXT:
            self._deny(404, "not found")
            return
        hit = self.uploads.read_bytes(token)
        if hit is None:
            # Expired links say so (410); everything else is a plain 404.
            self._deny(410 if self.uploads.expired(token) else 404,
                       "gone" if self.uploads.expired(token) else "not found")
            return
        record, data = hit
        self.send_response(200)
        self.send_header("Content-Type", record["mime"])
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_HEAD(self):
        self.do_GET()

    def _deny(self, code: int, message: str):
        body = message.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Quiet by default: the board process keeps its own logs.
        return


def make_server(host: str = "127.0.0.1", port: int | None = None,
                uploads: UploadStore | None = None) -> ThreadingHTTPServer:
    cfg = photohost_config()
    port = port if port is not None else cfg["port"]
    handler = type("BoundPhotoHostHandler", (PhotoHostHandler,),
                  {"uploads": uploads or UploadStore()})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def start_photohost(host: str = "127.0.0.1", port: int | None = None,
                    uploads: UploadStore | None = None) -> ThreadingHTTPServer:
    """Start the photo host in a daemon thread; returns the server handle."""
    server = make_server(host, port, uploads)
    thread = threading.Thread(target=server.serve_forever,
                              name="media-photohost", daemon=True)
    thread.start()
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ClawTeam photo host (loopback)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args(argv)
    cfg = photohost_config()
    port = args.port if args.port is not None else cfg["port"]
    server = make_server(args.host, port)
    print(f"photo host listening on http://{args.host}:{port} "
          f"(public origin: {cfg['public_origin'] or 'NOT CONFIGURED'})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
