# Developer guide

## Architecture

```text
MCP host ← stdio → local launcher ← Streamable HTTP + API key → hosted Chans MCP
                                                             → Core HTTP operations
```

The official SDK transports own framing, SSE and HTTP session handling. The bridge
forwards messages, including initialization, tool schemas, results, progress and
cancellation, while propagating the negotiated protocol version to HTTP headers.
There is no copied tool catalog or second authorization layer. Each process owns its
own connection. Server-side authorization remains effective on every request.

The shared suite verifies handshake-based MCP using protocol `2025-11-25`, with both
JSON and SSE responses. Modern handshake-free protocol revisions are not currently
part of the compatibility contract. stdio EOF and process signals close connections;
Windows uses the host's normal process termination behavior for SIGTERM.

## Development

```sh
npm ci --prefix packages/node
uv sync --project packages/python --locked --python 3.12
npm run check
npm test
uv run --project packages/python python scripts/check_versions.py

# Run a local launcher with CHANS_API_KEY configured:
node packages/node/src/cli.js
uv run --project packages/python chans-mcp
```

The same subprocess contract tests exercise both implementations against synthetic
loopback HTTP servers; no Chans operation or phone call is made. CI also installs
built artifacts outside the checkout and reruns the contract tests. See
[release setup](RELEASE.md) for publishing and partial-release recovery.

This repository uses a single `main` branch. Related repositories:
[Core](https://github.com/ai-chans/core) and
[frontend and documentation](https://github.com/ai-chans/frontend) require organization
access. They own product behavior and product-facing documentation respectively.
