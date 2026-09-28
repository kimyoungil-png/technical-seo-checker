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
            max_output_tokens=500,
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
    siteone_text: str,
    metrics: dict,
    api_key: str,
    model: str = DEFAULT_MODEL,
    checks=None,
):
    client = genai.Client(api_key=api_key)

    issue_rows = [
        row
        for row in (checks or [])
        if row.get("Status") in ("NG", "△")
    ]

    system_prompt = """
あなたはTechnical SEOチェック結果の要約担当です。

ルール:
- 入力されたチェック結果だけを根拠にする。
- NG・△の中から重要な内容だけを拾う。
- OK項目は原則触れない。
- 推測で問題を追加しない。
- 修正方法の詳細説明や優先順位表は作らない。
- 日本語で約2行、2文程度にまとめる。
- 1文目: 全体状況と主要な問題。
- 2文目: 最も重要な対応方針を簡潔に示す。
- 見出し、箇条書き、Markdownは使用しない。
"""

    user_prompt = f"""
対象URL:
{url}

NG・△項目:
{json.dumps(issue_rows, ensure_ascii=False, indent=2)}

Lighthouse metrics:
{json.dumps(metrics or {}, ensure_ascii=False, indent=2)}
"""

    last_error = None

    # First try the configured/default model. A stale GEMINI_MODEL value
    # should not break the report, so any model-level failure falls back.
    primary_attempts = (0, 2, 5) if model == DEFAULT_MODEL else (0, 2)

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
    for delay in (0, 3):
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
