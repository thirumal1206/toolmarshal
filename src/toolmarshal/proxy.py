"""Stdio MCP proxy: sits between client and server, logs every tools/call."""

import json
import os
import subprocess
import sys
import threading
from collections.abc import Callable, Iterable
from typing import Any, Protocol, TextIO

from toolmarshal.decision import Decision, Request
from toolmarshal.opa import check_opa

Decide = Callable[[Request], Decision]
OPA_ENV = "TOOLMARSHAL_OPA_URL"
DENIED = -32001


def decider_from_env() -> Decide | None:
    """Return an OPA-backed decider when ``TOOLMARSHAL_OPA_URL`` is set, else None (log only)."""
    url = os.environ.get(OPA_ENV)
    return (lambda request: check_opa(request, url)) if url else None


def _error(msg_id: object, message: str) -> bytes:
    if msg_id is None:
        return b""  # a notification has no one to reply to: drop silently
    body = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": DENIED, "message": message}}
    return (json.dumps(body) + "\n").encode()


def _error_batch() -> bytes:
    body = {"jsonrpc": "2.0", "id": None, "error": {"code": DENIED, "message": "batch tools/call"}}
    return (json.dumps(body) + "\n").encode()


def enforce(raw: bytes, decide: Decide | None, log: TextIO | None = None) -> bytes | None:
    """Return a JSON-RPC error to send back when ``raw`` must not be forwarded, else None.

    ``b""`` means drop without a reply (a denied notification).

    Fails closed: a ``tools/call`` that is malformed, batched or has no id is blocked.
    """
    if decide is None:
        return None
    try:
        msg: Any = json.loads(raw)
    except ValueError:
        return None
    if isinstance(msg, list):
        if any(isinstance(m, dict) and m.get("method") == "tools/call" for m in msg):
            return _error_batch()
        return None
    if not isinstance(msg, dict) or msg.get("method") != "tools/call":
        return None
    params = msg.get("params")
    name = params.get("name") if isinstance(params, dict) else None
    args = params.get("arguments", {}) if isinstance(params, dict) else None
    if not isinstance(name, str) or not isinstance(args, dict):
        return _error(msg.get("id"), "malformed tools/call")
    decision = decide(Request(tool=name, arguments=args))
    print(
        f"toolmarshal decision allow={decision.allow} reason={decision.reason!r}",
        file=log or sys.stderr,
        flush=True,
    )
    if decision.allow:
        return None
    return _error(msg.get("id"), "tool call denied by policy")


def log_if_tool_call(line: bytes, log: TextIO | None = None) -> None:
    """Write one JSON log line to stderr when ``line`` is a ``tools/call`` request."""
    try:
        msg = json.loads(line)
    except ValueError:
        return
    if not isinstance(msg, dict) or msg.get("method") != "tools/call":
        return
    params = msg.get("params") or {}
    entry = {"id": msg.get("id"), "tool": params.get("name"), "arguments": params.get("arguments")}
    # stdout is the protocol channel, so logs go to stderr
    print("toolmarshal " + json.dumps(entry), file=log or sys.stderr, flush=True)


class Sink(Protocol):
    """What ``pump`` needs from an output stream."""

    def write(self, data: bytes, /) -> object:
        """Write one message."""

    def flush(self) -> None:
        """Push buffered bytes out."""

    def close(self) -> None:
        """Close the stream."""


class LockedWriter:
    """Serialise whole-message writes from the two pump threads that share stdout."""

    def __init__(self, out: Sink) -> None:
        """Wrap ``out``."""
        self._out = out
        self._lock = threading.Lock()

    def write(self, data: bytes) -> None:
        """Write one whole message under the lock."""
        with self._lock:
            self._out.write(data)
            self._out.flush()

    def flush(self) -> None:
        """No-op: ``write`` already flushes."""

    def close(self) -> None:
        """Close the wrapped stream."""
        self._out.close()


def pump(
    src: Iterable[bytes],
    dst: Sink,
    inspect: Callable[[bytes], None] | None = None,
    guard: Callable[[bytes], bytes | None] | None = None,
    reply: Sink | None = None,
) -> None:
    """Copy newline-delimited messages from ``src`` to ``dst``, then close ``dst``.

    When ``guard`` returns bytes the message is not forwarded and those bytes go to ``reply``.
    """
    for line in src:
        if inspect:
            inspect(line)
        if guard and reply and (denied := guard(line)) is not None:
            if denied:
                reply.write(denied)
                reply.flush()
            continue
        dst.write(line)
        dst.flush()
    dst.close()


def main(argv: list[str] | None = None) -> int:
    """Run the MCP server given in ``argv`` and proxy stdio to it."""
    cmd = argv if argv is not None else sys.argv[1:]
    if not cmd:
        print("usage: toolmarshal <mcp server command> [args...]", file=sys.stderr)
        return 2
    # Command comes from the operator, never from the agent.
    child = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)  # noqa: S603
    assert child.stdin is not None  # noqa: S101 - guaranteed by PIPE
    assert child.stdout is not None  # noqa: S101
    out = LockedWriter(sys.stdout.buffer)
    decide = decider_from_env()
    threading.Thread(
        target=pump,
        args=(sys.stdin.buffer, child.stdin, log_if_tool_call, lambda b: enforce(b, decide), out),
        daemon=True,
    ).start()
    pump(child.stdout, out)
    return child.wait()


if __name__ == "__main__":
    sys.exit(main())
