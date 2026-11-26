# 0004 OPA runs as a server, and toolwall denies when it cannot get an answer

- Status: accepted
- Date: 2026-11-26

## Context

Item 02 made the decision a pure function over a static allowlist. Per agent rules, argument limits and identity will outgrow that, and they should change without a code release. Open Policy Agent (OPA) is the standard engine for this and reads rules written in Rego.

## Decision

Run OPA as a separate server and ask it once per request: `POST /v1/data/toolwall/allow` with `{"input": {agent, tool, arguments}}`. `toolwall.opa.check_opa` returns the same `Decision` as `check`. Only a literal `true` allows. Anything else denies: `false`, an undefined result, a wrong type, an HTTP error, a timeout or an unreachable server. The policy lives in `policy/`: `toolwall.rego` for the rule and `data.json` for the agent allowlists.

## Consequences

- Rules and allowlists change without touching Python, and a security owner can review them as files.
- The decision stays one call from the front ends, so item 03b can wire both proxies to it.
- OPA is now a runtime dependency that must be running next to toolwall. If it is down, every tool call is denied. That is the safe failure, and it is visible in the reason string.
- One local HTTP round trip per tool call. The OPA server holds the policy in memory, so the cost is small, but it is not zero.
- Python tests use a fake OPA server. The Rego itself is exercised by `opa test` in item 04.
- `Request` gains an `agent` field, defaulting to `anonymous`. Real identity from a token arrives in item 05.

## Alternatives considered

- `opa eval` as a subprocess per call: no server to run, but it starts a process on every tool call.
- OPA compiled to WebAssembly inside the process: no network hop, but a heavy dependency this early.
- Keep growing `check` in Python: fine for one allowlist, but every rule change becomes a code change and a release.
