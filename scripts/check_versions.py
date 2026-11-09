"""Keep the two distributions and runtime versions on one release number."""

import json
import os
import re
import tomllib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = json.loads((root / "packages/node/package.json").read_text())["version"]
python = tomllib.loads((root / "packages/python/pyproject.toml").read_text())["project"]["version"]
assert re.fullmatch(r"\d+\.\d+\.\d+", version), "Use a stable semantic version"
assert version == python, "npm and PyPI versions must match"
assert f"VERSION = '{version}'" in (root / "packages/node/src/bridge.js").read_text()
assert (
    f'__version__ = "{version}"' in (root / "packages/python/src/chans_mcp/__init__.py").read_text()
)
tag = os.environ.get("GITHUB_REF", "")
if tag.startswith("refs/tags/"):
    assert tag == f"refs/tags/v{version}", "Tag must match both package versions"
print(version)
