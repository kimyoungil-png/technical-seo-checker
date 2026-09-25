import os
import json
import subprocess
import tempfile
from urllib.parse import urlparse
from pathlib import Path

NODE_DIR = Path.home() / "node22"
NODE_BIN = NODE_DIR / "bin" / "node"
NPX_BIN = NODE_DIR / "bin" / "npx"


def ensure_node():
    if NODE_BIN.exists() and NPX_BIN.exists():
        return

    result = subprocess.run(
        ["bash", "setup_node.sh"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Node.js 22 のセットアップに失敗しました。\n"
            + result.stderr
        )


def run_unlighthouse(url: str):
    ensure_node()

    parsed = urlparse(url)

    base = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path or "/"

    workdir = Path(
        tempfile.mkdtemp(prefix="unlighthouse-")
    )

    env = os.environ.copy()

    env["PATH"] = (
        f"{NODE_DIR / 'bin'}:"
        + env.get("PATH", "")
    )

    env["CHROME_PATH"] = "/usr/bin/chromium"

    cmd = [
        str(NPX_BIN),
        "--yes",
        "unlighthouse@0.18.1",
        "ci",
        "--site",
        base,
        "--urls",
        path,
        "--output-path",
        str(workdir),
        "--reporter",
        "jsonExpanded",
        "--no-cache",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=240,
        env=env,
    )

    json_files = list(
        workdir.rglob("*.json")
    )

    reports = []

    for file in json_files:
        try:
            with open(
                file,
                "r",
                encoding="utf-8",
            ) as f:
                data = json.load(f)

            reports.append({
                "file": str(file),
                "data": data,
            })

        except Exception:
            pass

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "reports": reports,
        "workdir": str(workdir),
    }
