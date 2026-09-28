import json
import time
import urllib.error
import urllib.request


CLOUD_RUN_API = (
    "https://technical-seo-unlighthouse-api-231228645606."
    "asia-northeast1.run.app/audit"
)


def _request_unlighthouse(url: str):
    payload = json.dumps({"url": url}).encode("utf-8")

    request = urllib.request.Request(
        CLOUD_RUN_API,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=210,
    ) as response:
        body = response.read().decode("utf-8")

    data = json.loads(body)

    if data.get("success"):
        return {
            "returncode": 0,
            "stderr": "",
            "metrics": data.get("metrics", {}),
        }

    return {
        "returncode": 1,
        "stderr": data.get("error") or "Unlighthouse API error",
        "metrics": {},
    }


def run_unlighthouse(url: str):
    last_error = ""

    for attempt in range(2):
        try:
            result = _request_unlighthouse(url)
            if result.get("returncode") == 0:
                return result
            last_error = result.get("stderr", "")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            last_error = (
                f"Cloud Run HTTP Error {e.code}\n"
                f"{error_body}"
            )
        except Exception as e:
            last_error = str(e)

        if attempt == 0:
            time.sleep(3)

    return {
        "returncode": 1,
        "stderr": last_error or "Unlighthouse API error",
        "metrics": {},
    }
