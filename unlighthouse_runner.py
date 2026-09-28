import json
import urllib.request
import urllib.error


CLOUD_RUN_API = (
    "https://technical-seo-unlighthouse-api-231228645606."
    "asia-northeast1.run.app/audit"
)


def run_unlighthouse(url: str):

    payload = json.dumps({
        "url": url
    }).encode("utf-8")

    request = urllib.request.Request(
        CLOUD_RUN_API,
        data=payload,
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=180
        ) as response:

            body = response.read().decode("utf-8")

        data = json.loads(body)

        if data.get("success"):

            return {
                "returncode": 0,
                "stdout": data.get("stdout", ""),
                "stderr": "",
                "reports": [
                    {
                        "data": report
                    }
                    for report in data.get(
                        "reports",
                        []
                    )
                ],
            }

        return {
            "returncode": 1,
            "stdout": data.get("stdout", ""),
            "stderr": (
                data.get("stderr")
                or data.get("error")
                or "Unlighthouse API error"
            ),
            "reports": [],
        }

    except urllib.error.HTTPError as e:

        error_body = e.read().decode(
            "utf-8",
            errors="ignore"
        )

        return {
            "returncode": 1,
            "stdout": "",
            "stderr": (
                f"Cloud Run HTTP Error "
                f"{e.code}\n{error_body}"
            ),
            "reports": [],
        }

    except Exception as e:

        return {
            "returncode": 1,
            "stdout": "",
            "stderr": str(e),
            "reports": [],
        }
