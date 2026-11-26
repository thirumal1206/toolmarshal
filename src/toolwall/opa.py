"""Decision point backed by an OPA server: one HTTP call per request, fails closed."""

import json
from urllib.request import Request as HttpRequest
from urllib.request import urlopen

from toolwall.decision import Decision, Request


def check_opa(request: Request, url: str, timeout: float = 2.0) -> Decision:
    """Ask OPA at ``url`` (e.g. http://127.0.0.1:8181/v1/data/toolwall/allow). Deny on any doubt."""
    payload = {
        "input": {"agent": request.agent, "tool": request.tool, "arguments": request.arguments}
    }
    http = HttpRequest(  # noqa: S310 - url is operator config, never agent input
        url, json.dumps(payload).encode(), {"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urlopen(http, timeout=timeout) as resp:  # noqa: S310
            result = json.load(resp).get("result")
    except (OSError, ValueError, AttributeError) as exc:
        return Decision(allow=False, reason=f"opa unavailable, denied: {exc}")
    who = f"agent '{request.agent}' tool '{request.tool}'"
    if result is True:
        return Decision(allow=True, reason=f"opa allowed {who}")
    return Decision(allow=False, reason=f"opa denied {who}")
