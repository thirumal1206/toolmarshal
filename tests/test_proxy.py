import io
import json
import subprocess
import sys

import pytest

from toolmarshal.proxy import log_if_tool_call, main, pump

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
