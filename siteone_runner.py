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

    # 古い展開結果を削除
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

    # 実行ファイルを探す
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

    output_file = "/tmp/siteone-result.txt"

    if os.path.exists(output_file):
        os.remove(output_file)

    cmd = [
        binary,
        f"--url={url}",
        "--single-page",
        f"--output-text-file={output_file}",
        "--no-color",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )

    text_output = ""

    if os.path.exists(output_file):
        with open(
            output_file,
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as f:
            text_output = f.read()

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "report": text_output,
        "binary": binary,
    }
