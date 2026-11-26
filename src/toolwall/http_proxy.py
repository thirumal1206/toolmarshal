"""Streamable HTTP MCP proxy: forwards to one upstream endpoint, logs every tools/call."""

import argparse
import sys
from http.client import HTTPConnection, HTTPSConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from toolwall.proxy import log_if_tool_call

# Hop-by-hop or recomputed by this proxy; everything else, Mcp-Session-Id included, passes.
_DROP = {"host", "connection", "keep-alive", "transfer-encoding", "content-length"}


def make_handler(upstream: str) -> type[BaseHTTPRequestHandler]:
    """Build a request handler class bound to the upstream MCP endpoint URL."""
    url = urlsplit(upstream)
    conn_cls = HTTPSConnection if url.scheme == "https" else HTTPConnection
    path = url.path or "/"

    class Handler(BaseHTTPRequestHandler):
        # HTTP/1.0: response ends when the connection closes, so SSE streams need no framing.
        protocol_version = "HTTP/1.0"

        def _forward(self) -> None:
            size = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(size) if size else None
            if body is not None and self.command == "POST":
                log_if_tool_call(body)
            headers = {k: v for k, v in self.headers.items() if k.lower() not in _DROP}
            conn = conn_cls(url.netloc, timeout=300)
            try:
                conn.request(self.command, path, body, headers)
                resp = conn.getresponse()
            except OSError as exc:
                conn.close()
                self.log_error("upstream error: %s", exc)
                self.send_error(502, "upstream unreachable")
                return
            try:
                self.send_response(resp.status, resp.reason)
                for k, v in resp.getheaders():
                    if k.lower() not in _DROP:
                        self.send_header(k, v)
                self.end_headers()
                # read1 returns as soon as bytes arrive, so SSE events are not held back
                while chunk := resp.read1(65536):
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except OSError as exc:
                self.log_error("stream closed: %s", exc)
            finally:
                conn.close()

        do_POST = do_GET = do_DELETE = _forward

    return Handler


def main(argv: list[str] | None = None) -> int:
    """Listen on localhost and proxy Streamable HTTP to the upstream MCP endpoint."""
    parser = argparse.ArgumentParser(prog="toolwall-http")
    parser.add_argument("upstream", help="upstream MCP endpoint, e.g. http://127.0.0.1:9000/mcp")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    # Localhost only: MCP spec warns local servers bound wider are open to DNS rebinding.
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.upstream))
    print(f"toolwall-http listening on 127.0.0.1:{server.server_port}", file=sys.stderr)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
