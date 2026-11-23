# Backlog

One item per day. Each item ships code with a test and a `learn/NN-topic.md` note with one diagram.

- [ ] 01 MCP proxy: stdio and HTTP passthrough that logs every `tools/call`. Learn: MCP message flow (initialize, tools/list, tools/call)
- [ ] 02 Decision API: `check(request) -> allow|deny + reason`, static allowlist. Learn: policy decision point vs enforcement point
- [ ] 03 OPA integration, first Rego policy (tool allowlist per agent). Learn: Rego basics
- [ ] 04 Argument rules in Rego (amount limits, path globs, domain allowlists). Learn: writing testable policy, `opa test`
- [ ] 05 Agent identity from JWT claims, on behalf of user. Learn: OAuth 2.1 and how MCP auth works
- [ ] 06 Token exchange (RFC 8693): swap user token for short lived per tool token. Learn: delegation chains
- [ ] 07 Spend budget per run: deny when cost limit hit. Learn: token accounting
- [ ] 08 Taint flag: requests shaped by untrusted content need stricter policy. Learn: lethal trifecta, CaMeL idea
- [ ] 09 Human approval path (deny with `needs_approval`, approve via webhook). Learn: async approval patterns
- [ ] 10 OTel GenAI spans and audit log. Learn: OTel GenAI semantic conventions
- [ ] 11 Dry run mode (log would-deny, never block). Learn: K8s admission audit/warn/enforce rollout
- [ ] 12 Plug into agentgateway or LiteLLM as external authz. Learn: ext_authz pattern
- [ ] 13 Helm chart, kind demo, policy library for OWASP agentic risks. Learn: shipping a policy pack
- [ ] 14 README demo GIF, architecture doc, v0.1 release
