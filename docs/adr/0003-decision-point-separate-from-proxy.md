# 0003 Decision logic is a pure function, separate from the proxy

- Status: accepted
- Date: 2026-11-25

## Context

The stdio and HTTP front ends both need an allow or deny answer for each `tools/call`. Later items replace the static allowlist with OPA, identity and budgets. The front ends must not change when that happens.

## Decision

`toolmarshal.decision.check(request, allowlist) -> Decision` is a pure function over plain data. It does no I/O and knows nothing about transports. Default deny. Every decision carries a reason string.

## Consequences

- One policy path for every transport, testable without processes or sockets.
- Swapping the allowlist for OPA later changes the body of `check`, not its callers.
- Wiring `check` into the proxies is a separate step, so this change blocks nothing yet.
- The signature will grow (agent identity, context), which is an API change we accept.

## Alternatives considered

- Check inside each proxy: duplicates policy per transport and couples it to I/O.
- A policy class with a plugin interface: one implementation today, so a function is enough.
