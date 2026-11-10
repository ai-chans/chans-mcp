# Chans MCP

Connect your MCP client to Chans. Get an API key from Chans **Developer settings → API keys**.

## Connect directly over HTTP (recommended)

No package installation is needed. Use `https://api.chans.ai/mcp/` and send your
API key in the `Authorization` header.

### Cursor

Open `~/.cursor/mcp.json`, paste the configuration below, and replace the API key.
If `mcpServers` already exists, add only the `chans` entry inside it.

```json
{
  "mcpServers": {
    "chans": {
      "url": "https://api.chans.ai/mcp/",
      "headers": {
        "Authorization": "Bearer YOUR_CHANS_API_KEY"
      }
    }
  }
}
```

[Cursor setup reference](https://prod.cursor.com/help/customization/mcp).

### Claude Code

```sh
claude mcp add --scope user --transport http chans https://api.chans.ai/mcp/ --header "Authorization: Bearer YOUR_CHANS_API_KEY"
```

Run `claude mcp list` to check the connection, or `/mcp` inside Claude Code.
For JSON configuration in `.mcp.json`, use the Cursor example above and add
`"type": "http"` to the `chans` entry.
[Claude Code setup reference](https://code.claude.com/docs/en/mcp).

### VS Code

Run **MCP: Open User Configuration** from the Command Palette and paste:

```json
{
  "servers": {
    "chans": {
      "type": "http",
      "url": "https://api.chans.ai/mcp/",
      "headers": {
        "Authorization": "Bearer YOUR_CHANS_API_KEY"
      }
    }
  }
}
```

Save, then use **MCP: List Servers** to start `chans`.
[VS Code setup reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration).

### Dev and custom headers

For Cursor, use this configuration. For Claude Code, add `"type": "http"` inside
`chans-dev`. For VS Code, also change `mcpServers` to `servers`.

```json
{
  "mcpServers": {
    "chans-dev": {
      "url": "https://dev-api.chans.ai/mcp/",
      "headers": {
        "Authorization": "Bearer YOUR_DEV_CHANS_API_KEY",
        "CF-Access-Client-Id": "YOUR_CF_CLIENT_ID",
        "CF-Access-Client-Secret": "YOUR_CF_CLIENT_SECRET",
        "X-Custom-Header": "YOUR_VALUE"
      }
    }
  }
}
```

Add any application headers your endpoint needs. Cloudflare's header names use
hyphens as shown above; your Access policy must allow the service token.
Direct connections use your MCP client's header handling.
[Cloudflare service-token setup](https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/).

## Use npx or uvx (stdio)

Use the launcher when your client requires a local command, including the
Claude Desktop **Settings → Developer → Edit Config** setup.
You need Node.js 22+ for npx, or uv and Python 3.12+ for uvx.
No global package installation is needed.

Paste one configuration below, replace the API key, save, and restart your client.

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

[Claude Desktop setup reference](https://modelcontextprotocol.io/docs/develop/connect-local-servers).

### Custom headers with stdio

Use `--header "Name: value"` for each header. With **0.1.4+**, this configuration
needs no environment variables:

```json
{
  "mcpServers": {
    "chans-dev": {
      "command": "npx",
      "args": [
        "-y", "@ai-chans/mcp",
        "--url", "https://dev-api.chans.ai/mcp/",
        "--header", "Authorization: Bearer YOUR_DEV_CHANS_API_KEY",
        "--header", "CF-Access-Client-Id: YOUR_CF_CLIENT_ID",
        "--header", "CF-Access-Client-Secret: YOUR_CF_CLIENT_SECRET",
        "--header", "X-Custom-Header: YOUR_VALUE"
      ]
    }
  }
}
```

For uvx, use `"command": "uvx"` and replace the first two arguments with
`"chans-mcp"`. The same flags work with `doctor`. `--url` overrides
`CHANS_MCP_URL`; it defaults to production when neither is set.

A stdio client does not forward a top-level `headers` field to its child process.
Use the arguments above. `CHANS_API_KEY` remains supported instead of an explicit
Authorization header; do not configure both. The Cloudflare environment variables
from 0.1.3 remain supported for existing configurations.

Headers are checked for valid HTTP names and printable ASCII values. Control
characters (including CR/LF), duplicate names ignoring case, and HTTP/MCP transport
header overrides are rejected. The limit is 64 headers and 16 KiB in total.
Credentials are not printed or forwarded across origins. Header values are not
HTML-escaped or otherwise rewritten; validation protects HTTP framing.

### Other stdio clients

Choose **stdio** and enter:

| Field | npx | uvx |
|---|---|---|
| Command | `npx` | `uvx` |
| Arguments | `-y`, `@ai-chans/mcp` | `chans-mcp` |
| Environment | `CHANS_API_KEY=YOUR_CHANS_API_KEY` | `CHANS_API_KEY=YOUR_CHANS_API_KEY` |

On Windows, use `npx.cmd` if your app cannot launch `npx`. If a command cannot be
found, use its full executable path.

Both connection methods use the tools exposed by Chans Core. Your API key's scopes
determine which tools are available. Keep credentials out of shared configuration files.

[Development](https://github.com/ai-chans/chans-mcp/blob/main/DEVELOPMENT.md) ·
[Releases](https://github.com/ai-chans/chans-mcp/blob/main/RELEASE.md)
