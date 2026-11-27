import io
import json
import os
import subprocess
import sys

import pytest

from toolmarshal.decision import Decision, Request
from toolmarshal.proxy import (
    OPA_ENV,
    Decide,
    decider_from_env,
    enforce,
    log_if_tool_call,
    main,
    pump,
)

FAKE_SERVER = (
    "import sys, json\n"
    "for l in sys.stdin:\n"
    "    m = json.loads(l)\n"
    "    r = {'jsonrpc': '2.0', 'id': m['id'], 'result': {'echo': m['method']}}\n"
    "    print(json.dumps(r), flush=True)\n"
)


def _msg(**fields: object) -> bytes:
    return (json.dumps({"jsonrpc": "2.0", **fields}) + "\n").encode()


def test_logs_tool_call_with_name_and_arguments() -> None:
    log = io.StringIO()
    log_if_tool_call(
        _msg(id=3, method="tools/call", params={"name": "refund", "arguments": {"amount": 500}}),
        log,
    )
    entry = json.loads(log.getvalue().removeprefix("toolmarshal "))
    assert entry == {"id": 3, "tool": "refund", "arguments": {"amount": 500}}


@pytest.mark.parametrize(
    "line",
    [_msg(id=1, method="tools/list"), b"not json\n", b"[1, 2]\n"],
    ids=["other-method", "invalid-json", "non-object"],
)
def test_ignores_everything_else(line: bytes) -> None:
    log = io.StringIO()
    log_if_tool_call(line, log)
    assert log.getvalue() == ""


def test_pump_copies_inspects_and_closes() -> None:
    seen: list[bytes] = []
    dst = io.BytesIO()
    dst.close = lambda: None  # type: ignore[method-assign]  # keep buffer readable
    pump([b"a\n", b"b\n"], dst, seen.append)
    assert dst.getvalue() == b"a\n" + b"b\n"
    assert seen == [b"a\n", b"b\n"]


def test_main_without_command_prints_usage(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err


def test_end_to_end_passthrough() -> None:
    requests = [
        _msg(id=1, method="initialize", params={}),
        _msg(id=2, method="tools/call", params={"name": "refund", "arguments": {}}),
    ]
    out = subprocess.run(
        [sys.executable, "-m", "toolmarshal.proxy", sys.executable, "-c", FAKE_SERVER],
        input=b"".join(requests),
        capture_output=True,
        timeout=10,
        check=True,
    )
    replies = [json.loads(line)["result"]["echo"] for line in out.stdout.splitlines()]
    assert replies == ["initialize", "tools/call"]
    assert out.stderr.count(b"toolmarshal ") == 1


def _allow_only(tool: str) -> Decide:
    return lambda r: Decision(r.tool == tool, "test")


def test_enforce_is_off_without_a_decider() -> None:
    assert enforce(_msg(id=1, method="tools/call", params={"name": "x"}), None) is None


def test_enforce_allows_and_denies(capsys: pytest.CaptureFixture[str]) -> None:
    decide = _allow_only("search")
    allowed = _msg(id=1, method="tools/call", params={"name": "search", "arguments": {}})
    assert enforce(allowed, decide) is None
    denied = enforce(_msg(id=2, method="tools/call", params={"name": "refund"}), decide)
    assert denied is not None
    err = json.loads(denied)
    assert err["id"] == 2
    assert err["error"]["code"] == -32001
    assert "allow=False" in capsys.readouterr().err


@pytest.mark.parametrize(
    "line",
    [
        _msg(id=1, method="tools/call", params={"name": 5}),
        _msg(id=1, method="tools/call", params={"name": "search", "arguments": [1]}),
        _msg(id=1, method="tools/call"),
        b'[{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search"}}]\n',
    ],
    ids=["bad-name", "bad-arguments", "no-params", "batch"],
)
def test_enforce_fails_closed_on_malformed_or_batched_calls(line: bytes) -> None:
    assert enforce(line, _allow_only("search")) is not None


@pytest.mark.parametrize(
    "line",
    [_msg(id=1, method="tools/list"), b"not json\n", b"[1]\n"],
    ids=["other-method", "invalid-json", "non-call-batch"],
)
def test_enforce_ignores_other_traffic(line: bytes) -> None:
    assert enforce(line, _allow_only("search")) is None


def test_decider_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(OPA_ENV, raising=False)
    assert decider_from_env() is None
    monkeypatch.setenv(OPA_ENV, "http://127.0.0.1:1/v1/data/toolmarshal/allow")
    decide = decider_from_env()
    assert decide is not None
    assert not decide(Request("refund")).allow  # nothing listens on port 1: fails closed


def test_pump_blocks_denied_message_and_replies() -> None:
    dst, reply = io.BytesIO(), io.BytesIO()
    dst.close = lambda: None  # type: ignore[method-assign]
    pump(
        [b"ok\n", b"bad\n"],
        dst,
        guard=lambda b: b"denied\n" if b == b"bad\n" else None,
        reply=reply,
    )
    assert dst.getvalue() == b"ok\n"
    assert reply.getvalue() == b"denied\n"


def test_end_to_end_denies_when_opa_is_unreachable() -> None:
    requests = [
        _msg(id=1, method="initialize", params={}),
        _msg(id=2, method="tools/call", params={"name": "refund", "arguments": {}}),
    ]
    out = subprocess.run(
        [sys.executable, "-m", "toolmarshal.proxy", sys.executable, "-c", FAKE_SERVER],
        input=b"".join(requests),
        capture_output=True,
        timeout=10,
        check=True,
        env={**os.environ, OPA_ENV: "http://127.0.0.1:1/v1/data/toolmarshal/allow"},
    )
    replies = {json.loads(line)["id"]: json.loads(line) for line in out.stdout.splitlines()}
    assert replies[1]["result"]["echo"] == "initialize"
    assert replies[2]["error"]["code"] == -32001


def test_denied_notification_is_dropped_without_a_reply() -> None:
    deny = _allow_only("search")
    assert enforce(_msg(method="tools/call", params={"name": "refund"}), deny) == b""
    assert enforce(_msg(method="tools/call", params={"name": 5}), deny) == b""
    dst, reply = io.BytesIO(), io.BytesIO()
    dst.close = lambda: None  # type: ignore[method-assign]
    pump([b"bad\n"], dst, guard=lambda b: b"", reply=reply)
    assert dst.getvalue() == b""
    assert reply.getvalue() == b""
