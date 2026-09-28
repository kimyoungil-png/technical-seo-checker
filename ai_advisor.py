import json
import time
from google import genai
from google.genai import types


DEFAULT_MODEL = "gemini-flash-latest"
FALLBACK_MODEL = "gemini-3.1-flash-lite"


def _call_gemini(client, model, system_prompt, user_prompt):
    return client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=300,
        ),
    )


def _is_retryable_error(exc):
    text = str(exc).upper()
    return any(
        token in text
        for token in (
            "503",
            "UNAVAILABLE",
            "429",
            "RESOURCE_EXHAUSTED",
            "DEADLINE_EXCEEDED",
            "TIMEOUT",
        )
    )


def generate_ai_advice(
    url: str,
    metrics: dict,
    api_key: str,
    model: str = DEFAULT_MODEL,
    checks=None,
):
    client = genai.Client(api_key=api_key)

    checks = checks or []
    issue_rows = [
        {
            "No": row.get("No"),
            "Item": row.get("Item"),
            "Status": row.get("Status"),
            "Result": row.get("Result"),
            "Action": row.get("Action"),
        }
        for row in checks
        if row.get("Status") in ("NG", "△")
    ]
    status_rows = [
        {
            "No": row.get("No"),
            "Item": row.get("Item"),
            "Status": row.get("Status"),
        }
        for row in checks
    ]
    status_counts = {
        status: sum(1 for row in checks if row.get("Status") == status)
        for status in ("OK", "△", "NG", "—")
    }

    system_prompt = """
あなたはTechnical SEOチェック結果の要約担当です。

ルール:
- 入力されたチェック結果だけを根拠にする。
- 最初に全チェック項目の判定結果を踏まえた全体評価を1文で述べる。
- NGが0件なら、1文目は「重大なTechnical SEOエラーは検出されませんでした。」から始める。
- NGがある場合は、1文目でNG件数と重大な問題があることを簡潔に述べる。
- その後、NG・△の中から重要な内容だけを拾って具体的に説明する。
- OK項目の細かな説明は不要。
- 推測で問題を追加しない。
- 修正方法の詳細説明や優先順位表は作らない。
- 日本語で2〜3文程度にまとめる。
- 見出し、箇条書き、Markdownは使用しない。
"""

    user_prompt = f"""
対象URL:
{url}

判定件数:
{json.dumps(status_counts, ensure_ascii=False)}

全項目の判定:
{json.dumps(status_rows, ensure_ascii=False)}

NG・△項目の詳細:
{json.dumps(issue_rows, ensure_ascii=False)}

Lighthouse metrics:
{json.dumps(metrics or {}, ensure_ascii=False)}
"""

    last_error = None

    # First try the configured/default model. A stale GEMINI_MODEL value
    # should not break the report, so any model-level failure falls back.
    primary_attempts = (0, 2)

    for delay in primary_attempts:
        if delay:
            time.sleep(delay)
        try:
            response = _call_gemini(
                client,
                model,
                system_prompt,
                user_prompt,
            )
            text = response.text or ""
            if not text.strip():
                raise RuntimeError("Gemini returned an empty response")
            return {
                "text": text,
                "model": model,
                "fallback_used": False,
            }
        except Exception as exc:
            last_error = exc
            if not _is_retryable_error(exc):
                break

    # Stable low-cost fallback for short summaries.
    for delay in (0,):
        if delay:
            time.sleep(delay)
        try:
            response = _call_gemini(
                client,
                FALLBACK_MODEL,
                system_prompt,
                user_prompt,
            )
            text = response.text or ""
            if not text.strip():
                raise RuntimeError("Gemini fallback returned an empty response")
            return {
                "text": text,
                "model": FALLBACK_MODEL,
                "fallback_used": True,
            }
        except Exception as exc:
            last_error = exc
            if not _is_retryable_error(exc):
                break

    raise RuntimeError(
        f"Gemini APIからまとめを取得できませんでした: {last_error}"
    ) from last_error
