# Chans MCP

Paste this into your MCP client configuration. Replace `<your-api-key>` with a key
from Chans **Developer settings → API keys**, then reload your client.

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

If you already have an `mcpServers` section, add the `chans` entry inside it.

Requires Node.js 22+ with npm.

[Source and support](https://github.com/ai-chans/chans-mcp)
