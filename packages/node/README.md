# Chans MCP

Native Node.js stdio bridge to Chans's hosted Streamable HTTP MCP service.
Requires Node.js 22+ and npm.

```sh
npx -y @ai-chans/mcp
```

Set `CHANS_API_KEY` in your MCP client's environment. The default endpoint is
`https://api.chans.ai/mcp/`; set `CHANS_MCP_URL` to override it. Remote endpoints
require HTTPS. HTTP is supported only for loopback development.

`npx -y @ai-chans/mcp doctor` authenticates and lists tools without executing them.
Diagnostics go to stderr; stdout is reserved for MCP messages. Interrupted tool
calls are never automatically replayed: check their status before retrying.

This connects to the hosted service; it does not run the Chans backend locally.
See https://github.com/ai-chans/chans-mcp for client configuration, development,
release instructions and support.
