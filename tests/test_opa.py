import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

import pytest

from toolwall.decision import Request
from toolwall.opa import check_opa


class FakeOpa(BaseHTTPRequestHandler):
    reply: ClassVar[tuple[int, bytes]] = (200, b'{"result": true}')
    seen: ClassVar[dict[str, object]] = {}

    def log_message(self, format: str, *args: object) -> None:
        pass

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers["Content-Length"]))
        FakeOpa.seen = {"path": self.path, "body": json.loads(body)}
        status, data = FakeOpa.reply
        self.send_response(status)
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def opa_url() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpa)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/v1/data/toolwall/allow"
    server.shutdown()
    server.server_close()


def _ask(url: str, reply: tuple[int, bytes]) -> bool:
    FakeOpa.reply = reply
    return check_opa(Request("refund", {"amount": 5}, agent="support-bot"), url).allow


def test_true_allows_and_input_carries_agent_tool_and_arguments(opa_url: str) -> None:
    decision = check_opa(Request("refund", {"amount": 5}, agent="support-bot"), opa_url)
    assert decision.allow
    assert "support-bot" in decision.reason
    assert FakeOpa.seen["path"] == "/v1/data/toolwall/allow"
    assert FakeOpa.seen["body"] == {
        "input": {"agent": "support-bot", "tool": "refund", "arguments": {"amount": 5}}
    }


@pytest.mark.parametrize(
    "reply",
    [
        (200, b'{"result": false}'),
        (200, b"{}"),
        (200, b'{"result": "yes"}'),
        (200, b'{"result": 1}'),
    ],
    ids=["false", "undefined", "string", "number"],
)
def test_anything_but_true_denies(opa_url: str, reply: tuple[int, bytes]) -> None:
    assert not _ask(opa_url, reply)


@pytest.mark.parametrize(
    "reply",
    [(500, b"boom"), (200, b"not json"), (200, b"[1]")],
    ids=["http-error", "bad-json", "not-an-object"],
)
def test_bad_replies_fail_closed(opa_url: str, reply: tuple[int, bytes]) -> None:
    FakeOpa.reply = reply
    decision = check_opa(Request("refund"), opa_url)
    assert not decision.allow
    assert "unavailable" in decision.reason


def test_unreachable_opa_fails_closed() -> None:
    dead = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpa)
    port = dead.server_port
    dead.server_close()
    decision = check_opa(Request("refund"), f"http://127.0.0.1:{port}/x", timeout=0.5)
    assert not decision.allow
    assert "unavailable" in decision.reason
