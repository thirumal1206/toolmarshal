# 0001 Transparent stdio line proxy, standard library only

- Status: accepted
- Date: 2026-11-24

## Context

toolwall must see every `tools/call` before it reaches an MCP server, without the client or server knowing it is there. The stdio transport sends one JSON-RPC message per line and forbids newlines inside a message.

## Decision

Run the server as a child process and copy lines in both directions, one thread per direction. Only client to server lines are inspected. No dependencies beyond the standard library.

## Consequences

- Works with any stdio MCP server with zero configuration.
- The inspection hook becomes the enforcement point when policy lands.
- Line reading relies on the transport rule above; a server that breaks it breaks the proxy too.
- Streamable HTTP needs its own front end (backlog 01b).

## Alternatives considered

- Asyncio: no gain for two byte streams and harder to read.
- Using the MCP Python SDK: adds a dependency and couples toolwall to one SDK version.
