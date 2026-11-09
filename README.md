# Chans MCP

Paste this into your MCP client configuration. Replace `<your-api-key>` with a key
from Chans **Developer settings → API keys**, then reload your client.

## npx — Node.js 22+

```json
{
  "mcpServers": {
    "chans": {
      "command": "npx",
      "args": [
        "-y",
        "@ai-chans/mcp"
      ],
      "env": {
        "CHANS_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

## uvx — uv and Python 3.12+

```json
{
  "mcpServers": {
    "chans": {
      "command": "uvx",
      "args": [
        "chans-mcp"
      ],
      "env": {
        "CHANS_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

If you already have an `mcpServers` section, add the `chans` entry inside it.

Choose one configuration. Both connect to the hosted Chans service.

[Development](DEVELOPMENT.md) · [Releases](RELEASE.md)
