# toolwall

Policy firewall for agent tool calls. Decides whether *this agent* may call *this tool* with *these arguments* right now, before the call reaches the MCP server.

## Why

Guardrail libraries inspect text. Gateways route traffic. Nobody answers the authorisation question for tool calls: who is the agent, on whose behalf, which tool, which arguments, how much budget is left, and did untrusted content shape the request. OWASP Top 10 for Agentic Applications (2025) puts tool misuse and privilege abuse at the top; the MCP roadmap lists enterprise auth as open work.

toolwall does not replace a gateway. It plugs into one as a policy decision point, the way admission controllers plug into Kubernetes.

## How it works

```mermaid
sequenceDiagram
    participant A as Agent
    participant G as Gateway
    participant T as toolwall
    participant P as Policy (Rego / Cedar)
    participant M as MCP server
    A->>G: tools/call refund(order, 500)
    G->>T: check(identity, tool, args, taint, spend)
    T->>P: evaluate
    P-->>T: deny: amount > 100 needs approval
    T-->>G: deny + reason (audit log, OTel span)
    G-->>A: blocked
    Note over T,M: on allow: mint short lived scoped token, forward
```

## Status

Early. See [BACKLOG.md](BACKLOG.md).
