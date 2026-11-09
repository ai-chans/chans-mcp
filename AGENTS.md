# Chans MCP bridge

This public repository owns the npm `@ai-chans/mcp` and PyPI `chans-mcp` launchers.
Use only `main`; do not add a dev branch. Keep both packages on the same version.

- Reuse official MCP transports. Custom code connects transports, validates local
  configuration and handles process lifecycle; it must not copy product tools.
- Core (`ai-chans/core`) owns HTTP contracts, MCP tools, authorization, scopes and
  business operations. Frontend (`ai-chans/frontend`) owns product documentation.
- Forward protocol messages without changing IDs, schemas, annotations or results.
  Do not invent capabilities, execute connectivity-probe tools or replay tool POSTs.
- stdout is protocol-only during serving. Never print credentials or raw HTTP errors.
  Keep remote HTTPS and cross-origin credential protection covered by tests.
- Run `npm ci --prefix packages/node`, `uv sync --project packages/python --locked`,
  `npm run check`, `npm test`, and `uv run --project packages/python python
  scripts/check_versions.py`. Packaging changes also require building and running
  `scripts/check_artifacts.py` against the exact distributions.
- Tests use synthetic loopback endpoints only. Do not use real keys or place calls.
- Update README for user behavior; release instructions live in RELEASE.md. Changes
  here do not deploy Core or frontend. Registry publication needs configured owners
  and trusted publishers; never claim a package is available before verifying it.
