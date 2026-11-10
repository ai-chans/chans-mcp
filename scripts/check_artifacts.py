"""Install built distributions outside the checkout, then run the shared contract."""

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
dist = root / "dist"
(wheel,) = dist.glob("*.whl")
(tarball,) = dist.glob("*.tgz")
npm = shutil.which("npm")
uv = shutil.which("uv")
assert npm and uv
# Verify npm recognizes the distribution as a local tarball before publication.
subprocess.run(
    [npm, "publish", str(tarball), "--dry-run", "--ignore-scripts", "--access", "public"],
    check=True,
)
with tempfile.TemporaryDirectory(prefix="chans-mcp-artifacts-") as folder:
    destination = Path(folder)
    environment = destination / "python"
    subprocess.run([uv, "venv", "--python", sys.executable, str(environment)], check=True)
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    subprocess.run([uv, "pip", "install", "--python", str(python), str(wheel)], check=True)
    node = destination / "node"
    subprocess.run(
        [npm, "install", "--prefix", str(node), "--ignore-scripts", str(tarball)],
        check=True,
    )
    node_cli = node / "node_modules/@ai-chans/mcp/src/cli.js"
    env = {
        **os.environ,
        "CHANS_PYTHON_COMMAND": shlex.join(
            [
                str(python),
                "-c",
                "from chans_mcp.cli import main; raise SystemExit(main())",
            ]
        ),
        "CHANS_NODE_COMMAND": shlex.join([shutil.which("node"), str(node_cli)]),
    }
    # Exercise the package's actual advertised entry points as well.
    python_cli = environment / (
        "Scripts/chans-mcp.exe" if sys.platform == "win32" else "bin/chans-mcp"
    )
    subprocess.run([str(python_cli), "--version"], cwd=destination, check=True)
    subprocess.run(
        [
            npm,
            "exec",
            "--offline",
            "--prefix",
            str(node),
            "--",
            "chans-mcp",
            "--version",
        ],
        cwd=destination,
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=root,
        env=env,
        check=True,
    )
