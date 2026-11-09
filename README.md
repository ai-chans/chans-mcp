# Chans MCP

Connect an MCP client that uses stdio to the hosted Chans MCP service.
Choose either native launcher:

```sh
npx -y @ai-chans/mcp
# or
uvx chans-mcp
```

These commands require a published release. Until the first release is published,
use the local development commands below. Node.js 22+ is required for npm; Python
3.12+ and uv are required for the Python package. Neither launcher needs the other
runtime. This bridge requires connectivity to Chans; it does not install the backend.

## Configure your MCP client

Create a scoped Chans API key in your workspace's developer settings. Give it only
the scopes required by the operations you want to make available. Store it through
your client's secret mechanism when available; keep configuration files private.

```json
{
  "mcpServers": {
    "chans": {
      "command": "npx",
      "args": ["-y", "@ai-chans/mcp@0.1.0"],
      "env": { "CHANS_API_KEY": "<your-api-key>" }
    }
  }
}
```

For Python, use `"command": "uvx"` and `"args": ["chans-mcp==0.1.0"]`.
Make sure your MCP client can find `npx` or `uvx` in its PATH. On Windows, a client
may require `npx.cmd` or the executable's absolute path.

| Environment variable | Behavior |
|---|---|
| `CHANS_API_KEY` | Required raw API key; sent as a Bearer credential |
| `CHANS_MCP_URL` | Optional; defaults to `https://api.chans.ai/mcp/` |

Remote endpoints require HTTPS. Plain HTTP is accepted only for `localhost`,
`127.0.0.1` and `::1`. URL credentials, query strings and fragments are rejected.
Redirects cannot send credentials to a different origin. Existing MCP clients with
native Streamable HTTP support can connect directly to the hosted endpoint.

## Check the connection

With `CHANS_API_KEY` set in your environment:

```sh
npx -y @ai-chans/mcp doctor
# or
uvx chans-mcp doctor
```

`doctor` authenticates and counts authorized tools across discovery pages. It never
calls a tool. `--help` and `--version` work without credentials.

Serving writes only MCP JSON-RPC to stdout; diagnostics use stderr. Interrupted
operations may already have completed. The bridge never automatically replays a
failed tool POST: inspect the operation's status before retrying.

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
