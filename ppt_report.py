import base64
import json
import urllib.error
import urllib.request


CLOUD_RUN_REPORT_API = (
    "https://technical-seo-unlighthouse-api-231228645606."
    "asia-northeast1.run.app/report-ppt"
)


def build_ppt_report(
    url: str,
    checks: list[dict],
    summary: str = "",
):
    payload = json.dumps(
        {
            "url": url,
            "checks": checks,
            "summary": summary or "",
        },
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        CLOUD_RUN_REPORT_API,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=120,
        ) as response:
            body = response.read().decode("utf-8")

        data = json.loads(body)

        if not data.get("success"):
            raise RuntimeError(
                data.get("error")
                or "PowerPoint generation failed"
            )

        encoded = data.get("fileBase64")
        if not encoded:
            raise RuntimeError(
                "PowerPoint data was not returned"
            )

        return {
            "bytes": base64.b64decode(encoded),
            "filename": (
                data.get("filename")
                or "technical-seo-report.pptx"
            ),
        }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode(
            "utf-8",
            errors="ignore",
        )

        raise RuntimeError(
            f"Cloud Run HTTP Error {e.code}: "
            f"{error_body}"
        ) from e
