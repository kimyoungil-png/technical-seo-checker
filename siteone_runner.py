import json
import os
import subprocess
import urllib.request
import tarfile
from pathlib import Path

SITEONE_VERSION = "2.5.1"

SITEONE_DIR = Path("/tmp/siteone")
SITEONE_BIN = SITEONE_DIR / "siteone-crawler" / "siteone-crawler"

DOWNLOAD_URL = (
    "https://github.com/janreges/siteone-crawler/releases/download/"
    f"v{SITEONE_VERSION}/"
    f"siteone-crawler-v{SITEONE_VERSION}-linux-x64.tar.gz"
)


def ensure_siteone():
    if SITEONE_BIN.is_file():
        SITEONE_BIN.chmod(0o755)
        return str(SITEONE_BIN)

    if SITEONE_DIR.exists():
        import shutil
        shutil.rmtree(SITEONE_DIR)

    SITEONE_DIR.mkdir(parents=True, exist_ok=True)

    archive_path = "/tmp/siteone.tar.gz"

    urllib.request.urlretrieve(
        DOWNLOAD_URL,
        archive_path,
    )

    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(SITEONE_DIR)

    candidates = [
        p
        for p in SITEONE_DIR.rglob("siteone-crawler")
        if p.is_file()
    ]

    if not candidates:
        raise RuntimeError(
            "SiteOne Crawlerの実行ファイルが見つかりませんでした。"
        )

    binary = candidates[0]
    binary.chmod(0o755)

    return str(binary)


def run_siteone(url: str):
    binary = ensure_siteone()

    text_file = "/tmp/siteone-result.txt"
    json_file = "/tmp/siteone-result.json"

    for path in (text_file, json_file):
        if os.path.exists(path):
            os.remove(path)

    cmd = [
        binary,
        f"--url={url}",
        "--single-page",
        f"--output-text-file={text_file}",
        f"--output-json-file={json_file}",
        "--no-color",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )

    text_output = ""
    json_data = {}

    if os.path.exists(text_file):
        with open(
            text_file,
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as f:
            text_output = f.read()

    if os.path.exists(json_file):
        try:
            with open(
                json_file,
                "r",
                encoding="utf-8",
                errors="ignore",
            ) as f:
                json_data = json.load(f)
        except Exception:
            json_data = {}

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "report": text_output,
        "data": json_data,
        "binary": binary,
    }
