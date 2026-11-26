# 0002 Streamable HTTP as a byte level reverse proxy, standard library only

- Status: accepted
- Date: 2026-11-24

## Context

Remote MCP servers use the Streamable HTTP transport: one endpoint, `POST` for client messages, replies as either JSON or an SSE stream, optional `GET` for a server stream, `DELETE` to end a session. The session is carried in the `Mcp-Session-Id` header. toolmarshal must see each `tools/call` without breaking any of this.

## Decision

Run a threaded `http.server` on localhost that forwards every request to one configured upstream endpoint with `http.client`. Read the request body to inspect it, then stream the response back byte for byte with `read1`. Respond as HTTP/1.0 so a closed connection marks the end of a stream and no chunked framing is needed. Pass all headers except hop by hop ones, so sessions and auth work unchanged. The proxy holds no session state.

## Consequences

- Same inspection hook as the stdio proxy, so policy lands in one place for both transports.
- Stateless: any number of proxies can sit in front of one server.
- One thread and one upstream connection per open request; long lived SSE streams each hold a thread. Fine for a sidecar, not for thousands of agents.
- No connection reuse to the upstream (HTTP/1.0 to the client, a fresh connection per request).
- Server to client messages on SSE streams are not inspected yet; only client requests are.

## Alternatives considered

- Asyncio with aiohttp or httpx: scales to many streams but adds a dependency before there is a need.
- Terminate MCP in the proxy with the MCP SDK and re-originate: full message awareness, but couples toolmarshal to one SDK and owns session state.
- Envoy or a gateway with ext_authz: the long term home (backlog 12), too heavy for learning the transport.
