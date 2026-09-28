import json
import time
from google import genai
from google.genai import types


DEFAULT_MODEL = "gemini-3.8-flash"
FALLBACK_MODEL = "gemini-3.5-flash-lite"


def _call_gemini(client, model, system_prompt, user_prompt):
    return client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            thinking_config=types.ThinkingConfig(
                thinking_level="low"
            ),
            max_output_tokens=3500,
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
あなたはシニアテクニカルSEOアナリストです。
新規公開・更新直後の1ページについてTechnical SEOチェック結果をレビューします。

ルール:
- 入力されたチェック結果だけを根拠にする。
- OK項目は原則コメント不要。
- NGと△を優先度順に整理する。
- 修正方法はWeb担当者・エンジニアがそのまま作業指示に使える具体性にする。
- Lighthouseはラボデータであり、実ユーザーのCore Web Vitalsそのものではない。
- 推測で問題を追加しない。
- 25項目を繰り返し説明しない。
- 日本語で簡潔に書く。

出力形式:
## 総合所見
3〜5文。

## 優先修正 TOP3
最大3項目。各項目は以下の形式。
### 項目名
- 優先度: 高 / 中
- 問題:
- 修正:
- 確認:

## 補足
必要な場合のみ2〜4文。
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

    for delay in (0, 2, 5):
        if delay:
            time.sleep(delay)
        try:
            response = _call_gemini(
                client,
                model,
                system_prompt,
                user_prompt,
            )
            return {
                "text": response.text or "",
                "model": model,
                "fallback_used": False,
            }
        except Exception as exc:
            last_error = exc
            if not _is_retryable_error(exc):
                raise

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
            return {
                "text": response.text or "",
                "model": FALLBACK_MODEL,
                "fallback_used": True,
            }
        except Exception as exc:
            last_error = exc
            if not _is_retryable_error(exc):
                raise

    raise RuntimeError(
        "Gemini APIが混雑しており、再試行とフォールバックモデルでも応答を取得できませんでした。"
    ) from last_error
