# Backlog

Items are built in list order, one per day. Each item ships code with a test and a `learn/NN-topic.md` note with one diagram.

- [x] 01a MCP proxy: stdio passthrough that logs every `tools/call`. Learn: MCP message flow (initialize, tools/list, tools/call)
- [x] 01b MCP proxy: Streamable HTTP passthrough that logs every `tools/call`. Learn: MCP HTTP transport and sessions
- [x] 02 Decision API: `check(request) -> allow|deny + reason`, static allowlist. Learn: policy decision point vs enforcement point
- [x] 03 OPA integration, first Rego policy (tool allowlist per agent). Learn: Rego basics
- [ ] 03b Enforce: both proxies call the decision and return a JSON-RPC error on deny. Learn: enforcement point behaviour and failing closed
- [ ] 03c AuthZEN endpoint: `POST /access/v1/evaluation` backed by OPA, with the discovery document, `X-Request-ID` and generic error bodies. Learn: PEP and PDP, the OpenID AuthZEN spec
- [ ] 04 Argument rules in Rego (amount limits, path globs, domain allowlists). Learn: writing testable policy, `opa test`
- [ ] 05 Agent identity from JWT claims, on behalf of user. Learn: OAuth 2.1 and how MCP auth works
- [ ] 06 Token exchange (RFC 8693): swap user token for short lived per tool token. Learn: delegation chains
- [ ] 08 Taint flag: requests shaped by untrusted content need stricter policy. Learn: lethal trifecta, CaMeL idea
- [ ] 10 OTel GenAI spans and audit log. Learn: OTel GenAI semantic conventions
- [ ] 12 Gateway demo: agentgateway as the enforcement point calling the AuthZEN endpoint, plus `tools/list` filtering. Learn: external authorisation in a real gateway (AuthZEN and ext_authz)
- [ ] 13 Helm chart, kind demo, policy library for OWASP agentic risks. Learn: shipping a policy pack
- [ ] 14 README demo GIF, architecture doc, v0.1 release

## Later

Other open source tools already ship these, so build the minimal version only after item 14. The numbers stay so links keep working.

- [ ] 07 Spend budget per run: deny when cost limit hit. Learn: token accounting
- [ ] 09 Human approval path (deny with `needs_approval`, approve via webhook). Learn: async approval patterns
- [ ] 11 Dry run mode (log would-deny, never block). Learn: K8s admission audit/warn/enforce rollout
