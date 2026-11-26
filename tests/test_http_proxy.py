import json
import threading
from collections.abc import Iterator
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from toolmarshal.http_proxy import main, make_handler


class FakeMcpServer(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass

    def do_POST(self) -> None:
        msg = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        body = json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": {"path": self.path}})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Mcp-Session-Id", "s-1")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        self.wfile.write(b"data: one\n\ndata: two\n\n")

    def do_DELETE(self) -> None:
        status = 204 if self.headers.get("Mcp-Session-Id") == "s-1" else 400
        self.send_response(status)
        self.end_headers()


def _serve(server: ThreadingHTTPServer) -> None:
    threading.Thread(target=server.serve_forever, daemon=True).start()


@pytest.fixture
def proxy_port() -> Iterator[int]:
    upstream = ThreadingHTTPServer(("127.0.0.1", 0), FakeMcpServer)
    proxy = ThreadingHTTPServer(
        ("127.0.0.1", 0), make_handler(f"http://127.0.0.1:{upstream.server_port}/mcp")
    )
    _serve(upstream)
    _serve(proxy)
    yield proxy.server_port
    proxy.shutdown()
    upstream.shutdown()


def _call(
    port: int, method: str, body: object = None, headers: dict[str, str] | None = None
) -> tuple[int, dict[str, str], bytes]:
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    data = json.dumps(body).encode() if body is not None else None
    conn.request(method, "/anything", data, headers or {})
    resp = conn.getresponse()
    out = resp.status, dict(resp.getheaders()), resp.read()
    conn.close()
    return out


def test_post_is_forwarded_to_upstream_path_and_tool_call_logged(
    proxy_port: int, capsys: pytest.CaptureFixture[str]
) -> None:
    call = {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "refund"}}
    status, headers, body = _call(proxy_port, "POST", call)
    assert status == 200
    assert headers["Mcp-Session-Id"] == "s-1"
    assert json.loads(body)["result"] == {"path": "/mcp"}
    assert '"tool": "refund"' in capsys.readouterr().err


def test_sse_stream_passes_through(proxy_port: int) -> None:
    status, headers, body = _call(proxy_port, "GET", headers={"Accept": "text/event-stream"})
    assert status == 200
    assert headers["Content-Type"] == "text/event-stream"
    assert body == b"data: one\n\ndata: two\n\n"


def test_session_header_reaches_upstream(proxy_port: int) -> None:
    assert _call(proxy_port, "DELETE", headers={"Mcp-Session-Id": "s-1"})[0] == 204


def test_unreachable_upstream_returns_502() -> None:
    dead = ThreadingHTTPServer(("127.0.0.1", 0), FakeMcpServer)
    dead_port = dead.server_port
    dead.server_close()
    proxy = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(f"http://127.0.0.1:{dead_port}"))
    _serve(proxy)
    try:
        assert _call(proxy.server_port, "GET")[0] == 502
    finally:
        proxy.shutdown()


def test_main_binds_localhost(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(ThreadingHTTPServer, "serve_forever", lambda self: None)
    assert main(["https://example.test/mcp", "--port", "0"]) == 0
    assert "listening on 127.0.0.1:" in capsys.readouterr().err
