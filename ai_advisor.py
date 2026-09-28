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
            max_output_tokens=700,
            temperature=0.1,
            response_mime_type="application/json",
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


def _parse_response(raw_text):
    text = (raw_text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty response")

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini returned invalid JSON") from exc

    summary = str(data.get("summary") or "").strip()
    if not summary:
        raise RuntimeError("Gemini summary was empty")

    proofreading = []
    for item in data.get("proofreading") or []:
        if not isinstance(item, dict):
            continue

        original = str(item.get("original") or "").strip()
        suggestion = str(item.get("suggestion") or "").strip()
        reason = str(item.get("reason") or "").strip()

        if not original or not suggestion:
            continue

        proofreading.append(
            {
                "original": original,
                "suggestion": suggestion,
                "reason": reason,
            }
        )

        if len(proofreading) >= 8:
            break

    return summary, proofreading


def generate_ai_advice(
    url: str,
    metrics: dict,
    api_key: str,
    model: str = DEFAULT_MODEL,
    checks=None,
    body_text: str = "",
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
あなたはTechnical SEOチェック結果の要約と、日本語本文の誤字脱字確認を担当します。

必ず次のJSONオブジェクトだけを返してください。
{
  "summary": "Technical SEOのまとめ",
  "proofreading": [
    {
      "original": "誤りを含む短い原文",
      "suggestion": "修正案",
      "reason": "誤字・脱字の理由"
    }
  ]
}

Technical SEOまとめのルール:
- 入力されたチェック結果だけを根拠にする。
- 最初に全チェック項目の判定結果を踏まえた全体評価を1文で述べる。
- NGが0件なら、1文目は「重大なTechnical SEOエラーは検出されませんでした。」から始める。
- NGがある場合は、1文目でNG件数と重大な問題があることを簡潔に述べる。
- その後、NG・△の中から重要な内容だけを拾って具体的に説明する。
- OK項目の細かな説明は不要。
- 推測で問題を追加しない。
- 日本語で2〜3文程度にまとめる。

本文の誤字脱字チェックのルール:
- SEO判定とは完全に分離する。
- 入力された本文テキストだけを確認する。
- 明確な誤字、脱字、助詞抜け、重複文字、明らかな変換ミスだけを指摘する。
- 表記ゆれ、好みの文体、言い換え、SEO改善、トーン改善は指摘しない。
- 固有名詞、商品名、サービス名は誤りだと断定できない限り指摘しない。
- 自信が低いものは出さない。
- 指摘は最大8件。
- 問題がなければ proofreading は空配列にする。
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

本文テキスト:
{body_text or "本文テキストを取得できず"}
"""

    last_error = None
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
            summary, proofreading = _parse_response(response.text)
            return {
                "text": summary,
                "proofreading": proofreading,
                "model": model,
                "fallback_used": False,
            }
        except Exception as exc:
            last_error = exc
            if not _is_retryable_error(exc):
                break

    try:
        response = _call_gemini(
            client,
            FALLBACK_MODEL,
            system_prompt,
            user_prompt,
        )
        summary, proofreading = _parse_response(response.text)
        return {
            "text": summary,
            "proofreading": proofreading,
            "model": FALLBACK_MODEL,
            "fallback_used": True,
        }
    except Exception as exc:
        last_error = exc

    raise RuntimeError(
        f"Gemini APIから結果を取得できませんでした: {last_error}"
    ) from last_error
