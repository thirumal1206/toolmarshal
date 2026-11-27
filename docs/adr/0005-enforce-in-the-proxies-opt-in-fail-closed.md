# 0005 The proxies enforce the decision when OPA is configured, and deny on anything unclear

- Status: accepted
- Date: 2026-11-27

## Context

Items 01a and 01b log tool calls and forward everything. Item 03 added a decision point backed by OPA. Something has to stop a denied call before it reaches the MCP server.

## Decision

Both proxies call `enforce(raw, decide)` for each client message. It returns a JSON-RPC error (code -32001, message `tool call denied by policy`) when the call must not be forwarded, and `None` otherwise. The stdio proxy writes the error to the client and drops the line. The HTTP proxy answers the POST with it and never contacts upstream.

Enforcement is switched on by `TOOLMARSHAL_OPA_URL`. Unset, the proxies only log, as before. Once it is set, these cases are denied:

- OPA says anything other than `true`, or cannot be reached.
- `tools/call` with a missing or non-string name, or non-object arguments.
- `tools/call` inside a JSON array. MCP no longer defines batching, and a batch would otherwise skip the check.

The client only sees a generic message. The reason goes to the proxy's stderr log.

## Consequences

- One code path for both transports, so rules cannot drift between them.
- Opt-in keeps existing setups working, but a missing variable means no enforcement. A later release should make enforcement the default and log only on request.
- Only client requests are checked. `tools/list` is not filtered yet (item 12), and server to client traffic is untouched.
- A denied call with no `id` (a notification) is dropped silently, because there is nobody to reply to.
- Every call is checked as agent `anonymous` until item 05.

## Alternatives considered

- Enforcement on by default with a required policy URL: safer, but breaks the log-only use and needs OPA to try the tool at all.
- Put the reason in the error body: useful for debugging, but it tells an attacker how the policy is built.
