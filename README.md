# Chans MCP

Connect Chans to your MCP client in three steps: choose a launcher, create an API
key, and paste the configuration below. No repository clone or global package
installation is needed.

## 1. Choose a launcher

**Use npx if you already have Node.js.** Choose uvx if you prefer Python. You only
need one of these options.

| Launcher | Requirements | Package |
|---|---|---|
| **npx** | [Node.js](https://nodejs.org/en/download) 22+ with npm | [@ai-chans/mcp](https://www.npmjs.com/package/@ai-chans/mcp) |
| **uvx** | [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.12+ | [chans-mcp](https://pypi.org/project/chans-mcp/) |

Check that your chosen launcher works. This downloads the package and prints its
version; no API key is needed yet.

**Node.js / npx**

```sh
npx -y @ai-chans/mcp --version
```

**Python / uvx**

```sh
uvx chans-mcp --version
```

## 2. Create a Chans API key

In your Chans workspace, open **Developer settings → API keys** and create a key
with the scopes you want your MCP client to use. Copy the key for the next step.

## 3. Add Chans to your MCP client

Open your client's MCP server configuration and add **one** of the following
entries. If you already have an `mcpServers` object, add `chans` inside it rather
than replacing your existing servers. The exact configuration location depends on
your client.

Replace `<your-api-key>` with your Chans API key. Use your client's secret storage
when available, and keep files containing the key private.

**Node.js / npx**

```json
{
  "mcpServers": {
    "chans": {
      "command": "npx",
      "args": ["-y", "@ai-chans/mcp"],
      "env": {
        "CHANS_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

**Python / uvx**

```json
{
  "mcpServers": {
    "chans": {
      "command": "uvx",
      "args": ["chans-mcp"],
      "env": {
        "CHANS_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

Save the configuration, then reload or restart your MCP client. It starts Chans
automatically and shows the tools available to your API key.

Chans connects to `https://api.chans.ai/mcp/`. It requires internet access and uses
the hosted Chans service; it does not install the backend on your computer.

## Check your connection

If your client cannot connect, run `doctor` in a terminal. It checks authentication
and tool discovery without executing a tool.

**macOS / Linux**

```sh
export CHANS_API_KEY="<your-api-key>"
npx -y @ai-chans/mcp doctor
# If you chose Python, use: uvx chans-mcp doctor
```

**Windows PowerShell**

```powershell
$env:CHANS_API_KEY = "<your-api-key>"
npx -y @ai-chans/mcp doctor
# If you chose Python, use: uvx chans-mcp doctor
```

A successful check reports how many authorized tools are available.

| Problem | What to check |
|---|---|
| `npx` or `uvx` cannot be found | Install the required runtime, then restart your MCP client. You may need to configure the launcher's absolute path. |
| Windows cannot launch `npx` | Try `npx.cmd` or the executable's absolute path in the client configuration. |
| Authentication fails | Check that `CHANS_API_KEY` contains the raw key, without a `Bearer ` prefix. |
| Expected tools are missing | Check the API key's scopes. |
| Running the launcher appears to wait | Without `doctor` or `--version`, it waits for MCP messages. Your MCP client normally starts and manages this process. |

## Optional settings

| Setting | How to use it |
|---|---|
| Another Chans deployment | Add `CHANS_MCP_URL` to the configuration's `env` object with its HTTPS MCP endpoint. |
| Pin version 0.1.0 with npx | Change the package argument to `@ai-chans/mcp@0.1.0`. |
| Pin version 0.1.0 with uvx | Change the package argument to `chans-mcp==0.1.0`. |

Remote endpoints require HTTPS. HTTP is accepted only for loopback development
(`localhost`, `127.0.0.1` or `::1`). URL credentials, query strings and fragments are
rejected; redirects cannot send credentials to a different origin.

If your client supports Streamable HTTP directly, it can connect to the hosted MCP
endpoint without this launcher. Interrupted tool calls may already have completed;
check their status before retrying. The bridge never automatically replays a failed
tool POST.

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
