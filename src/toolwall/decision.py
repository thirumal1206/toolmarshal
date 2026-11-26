"""Policy decision point: pure ``check`` with no I/O, so any enforcement point can call it."""

from collections.abc import Collection
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Request:
    """One tool call an agent wants to make."""

    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    """Verdict for a request, with a reason that is safe to log."""

    allow: bool
    reason: str


def check(request: Request, allowlist: Collection[str]) -> Decision:
    """Allow ``request`` only when its tool is in ``allowlist``. Default deny."""
    if request.tool in allowlist:
        return Decision(allow=True, reason=f"tool '{request.tool}' is allowlisted")
    return Decision(allow=False, reason=f"tool '{request.tool}' is not allowlisted")
