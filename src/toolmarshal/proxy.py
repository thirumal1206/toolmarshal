"""Stdio MCP proxy: sits between client and server, logs every tools/call."""

import json
import subprocess
import sys
import threading
from collections.abc import Callable, Iterable
from typing import IO, TextIO


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


def pump(
    src: Iterable[bytes], dst: IO[bytes], inspect: Callable[[bytes], None] | None = None
) -> None:
    """Copy newline-delimited messages from ``src`` to ``dst``, then close ``dst``."""
    for line in src:
        if inspect:
            inspect(line)
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
    threading.Thread(
        target=pump, args=(sys.stdin.buffer, child.stdin, log_if_tool_call), daemon=True
    ).start()
    pump(child.stdout, sys.stdout.buffer)
    return child.wait()


if __name__ == "__main__":
    sys.exit(main())
