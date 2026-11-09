# Releasing Chans MCP

The packages are `@ai-chans/mcp` on npm and `chans-mcp` on PyPI. All source work uses
`main`; releases use immutable `vX.Y.Z` tags. Version `0.1.0` is published on both
registries. The one-time setup below documents how to recreate the registry trust.

## One-time registry setup

1. Confirm npm publishing rights in the existing `ai-chans` organization. The first
   npm publication may require an authorized maintainer's local authenticated publish
   to create the package before its trusted publisher can be configured. Use the
   tested CI tarball, not an unreviewed local rebuild. Do not put a registry token in
   the repository. Confirm the registry's current bootstrap procedure at setup time.
2. In npm package settings, add GitHub Actions trusted publishing: owner `ai-chans`,
   repository `chans-mcp`, workflow `release.yml`, environment `npm`. Allow publishing.
3. In PyPI, register a pending trusted publisher for project `chans-mcp`: owner
   `ai-chans`, repository `chans-mcp`, workflow `release.yml`, environment `pypi`.
   An authorized PyPI account must own this setup.
4. GitHub environments `npm` and `pypi` are already configured for `v*` release tags.
   The workflow uses OIDC, with no
   long-lived publishing secrets. Both package registries are independent.

Official setup references: [npm](https://docs.npmjs.com/trusted-publishers/) and
[PyPI](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).

## Build and verify

Update versions in both package manifests, the Python `__init__.py`, and the Node
`VERSION` constant, plus README's pinned examples. Refresh locks with `npm install
--package-lock-only --prefix packages/node` and `uv lock --project packages/python`.
`scripts/check_versions.py` enforces agreement with the release tag.

```sh
mkdir -p dist
npm pack ./packages/node --pack-destination dist
uv build packages/python --out-dir dist
uv run --project packages/python python scripts/check_artifacts.py
```

CI runs on Linux, macOS and Windows, covering Node 22/24 and Python 3.12/3.14 across
the matrix. Release validation builds one set of artifacts, installs and tests those
exact files, and hands the same files to both publish jobs.

Once main is green, create and push the matching tag. The release workflow checks
that its commit belongs to main. It publishes each registry independently and then
verifies that exact version through its public registry API. The final job creates
a GitHub release with the tested artifacts.

## Partial-release recovery

Keep the tag and version unchanged. Rerun **failed jobs** in the same release run;
GitHub retains the successful validation artifact and completed publish jobs. Do not
rerun validation after successful publication or move the tag. The npm job checks
the published version's tarball integrity before treating it as already successful;
PyPI's action skips distributions that already exist. A registry publication cannot
be atomic across both services. Publish a new patch version to repair released code.

After release, verify both `npx -y @ai-chans/mcp@X.Y.Z --version` and
`uvx chans-mcp==X.Y.Z --version`, then enable the published commands in frontend
documentation. No release workflow deploys Core or frontend.
