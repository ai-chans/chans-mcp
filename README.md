# Chans MCP

Copy the configuration for your app below. Replace `YOUR_CHANS_API_KEY` with a key
from Chans **Developer settings → API keys**.

Use **npx** with Node.js 22+, or **uvx** with uv and Python 3.12+. No global package
installation is needed. Keep your API key private.

## Claude Desktop and Cursor

- **Claude Desktop:** open **Settings → Developer → Edit Config**.
- **Cursor:** open `~/.cursor/mcp.json` for your personal configuration.

Paste one of these configurations, save, and restart the app. If `mcpServers`
already exists, add only the `chans` entry inside it.

### With npx

```json
{
  "mcpServers": {
    "chans": {
      "command": "npx",
      "args": ["-y", "@ai-chans/mcp"],
      "env": {
        "CHANS_API_KEY": "YOUR_CHANS_API_KEY"
      }
    }
  }
}
```

### With uvx

```json
{
  "mcpServers": {
    "chans": {
      "command": "uvx",
      "args": ["chans-mcp"],
      "env": {
        "CHANS_API_KEY": "YOUR_CHANS_API_KEY"
      }
    }
  }
}
```

Setup references: [Claude Desktop](https://modelcontextprotocol.io/docs/develop/connect-local-servers)
and [Cursor](https://prod.cursor.com/help/customization/mcp).

## Claude Code

Run **one** command in your terminal:

**npx:**

```sh
claude mcp add --scope user --env CHANS_API_KEY=YOUR_CHANS_API_KEY --transport stdio chans -- npx -y @ai-chans/mcp
```

**uvx:**

```sh
claude mcp add --scope user --env CHANS_API_KEY=YOUR_CHANS_API_KEY --transport stdio chans -- uvx chans-mcp
```

Run `claude mcp list` to check the connection. Inside Claude Code, use `/mcp` to
inspect the server. [Claude Code setup reference](https://code.claude.com/docs/en/mcp).

## VS Code

Open the Command Palette and run **MCP: Open User Configuration**. Paste this
configuration, save, then use **MCP: List Servers** to start `chans`.

```json
{
  "servers": {
    "chans": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@ai-chans/mcp"],
      "env": {
        "CHANS_API_KEY": "YOUR_CHANS_API_KEY"
      }
    }
  }
}
```

For uvx, change `"command"` to `"uvx"` and `"args"` to `["chans-mcp"]`.
VS Code uses `servers` instead of `mcpServers`.
[VS Code configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration).

## Dev behind Cloudflare Access

With version **0.1.3+**, add the dev endpoint and your Cloudflare service-token
credentials to `env`:

```json
{
  "mcpServers": {
    "chans-dev": {
      "command": "npx",
      "args": ["-y", "@ai-chans/mcp"],
      "env": {
        "CHANS_MCP_URL": "https://dev-api.chans.ai/mcp/",
        "CHANS_API_KEY": "YOUR_DEV_CHANS_API_KEY",
        "CF_ACCESS_CLIENT_ID": "YOUR_CF_ACCESS_CLIENT_ID",
        "CF_ACCESS_CLIENT_SECRET": "YOUR_CF_ACCESS_CLIENT_SECRET"
      }
    }
  }
}
```

For uvx, use `"command": "uvx"` and `"args": ["chans-mcp"]`.
Both Cloudflare values are required together. They are sent as `CF-Access-Client-Id`
and `CF-Access-Client-Secret` headers alongside the Chans API key, including for
`doctor`. Your Cloudflare Access policy must allow that service token.
[Cloudflare service-token setup](https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/).

## Other MCP clients

Choose **stdio** as the transport and enter:

| Field | npx | uvx |
|---|---|---|
| Command | `npx` | `uvx` |
| Arguments | `-y`, `@ai-chans/mcp` | `chans-mcp` |
| Environment | `CHANS_API_KEY=YOUR_CHANS_API_KEY` | `CHANS_API_KEY=YOUR_CHANS_API_KEY` |

On Windows, use `npx.cmd` if your app cannot launch `npx`. If a command cannot be
found, use its full executable path. Chans connects to `https://api.chans.ai/mcp/`;
your API key's scopes determine which tools are available.

[Development](https://github.com/ai-chans/chans-mcp/blob/main/DEVELOPMENT.md) ·
[Releases](https://github.com/ai-chans/chans-mcp/blob/main/RELEASE.md)
