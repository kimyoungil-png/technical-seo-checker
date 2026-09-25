import os
import json
import subprocess
import tempfile
from urllib.parse import urlparse
from pathlib import Path


def run_unlighthouse(url: str):
    parsed = urlparse(url)

    base = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path or "/"

    workdir = Path(tempfile.mkdtemp(prefix="unlighthouse-"))

    cmd = [
        "npx",
        "unlighthouse-ci",
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
        timeout=180,
    )

    json_files = list(workdir.rglob("*.json"))

    reports = []

    for file in json_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
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
