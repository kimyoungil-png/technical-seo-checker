import json
import time

from google import genai
from google.genai import types


DEFAULT_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODELS = (
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
)


def build_fallback_summary(checks):
    checks = checks or []
    ng_rows = [row for row in checks if row.get("Status") == "NG"]
    warn_rows = [row for row in checks if row.get("Status") == "△"]

    if ng_rows:
        items = "、".join(
            str(row.get("Item") or "")
            for row in ng_rows[:2]
            if row.get("Item")
        )
        detail = f" 主な要修正項目は{items}です。" if items else ""
        return (
            f"重大なTechnical SEOエラーが{len(ng_rows)}件検出されました。"
            f"{detail} 公開意図と設定内容を確認し、優先して修正してください。"
        ).strip()

    if warn_rows:
        items = "、".join(
            str(row.get("Item") or "")
            for row in warn_rows[:2]
            if row.get("Item")
        )
        detail = f" 要確認項目は{items}などです。" if items else ""
        return (
            "重大なTechnical SEOエラーは検出されませんでした。"
            f"要確認（△）が{len(warn_rows)}件あります。{detail}"
            " 公開意図と設定内容が一致しているか確認してください。"
        ).strip()

    return (
        "重大なTechnical SEOエラーは検出されませんでした。"
        "全チェック項目で大きな問題は確認されませんでした。"
    )


def _call_gemini(
    client,
    model,
    system_prompt,
    user_prompt,
    max_output_tokens=700,
):
    return client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_output_tokens,
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


def _parse_response(
    raw_text,
    *,
    require_summary,
    include_proofreading,
):
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
    if require_summary and not summary:
        raise RuntimeError("Gemini summary was empty")

    proofreading = []
    if include_proofreading:
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
    include_summary: bool = True,
    include_proofreading: bool = True,
):
    if not include_summary and not include_proofreading:
        return {
            "text": "",
            "proofreading": [],
            "model": model,
            "fallback_used": False,
        }

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

    task_rules = []

    if include_summary:
        task_rules.append(
            """
Technical SEOまとめのルール:
- 入力されたチェック結果だけを根拠にする。
- 最初に全チェック項目の判定結果を踏まえた全体評価を1文で述べる。
- NGが0件なら、1文目は「重大なTechnical SEOエラーは検出されませんでした。」から始める。
- NGがある場合は、1文目でNG件数と重大な問題があることを簡潔に述べる。
- その後、NG・△の中から重要な内容だけを拾って具体的に説明する。
- OK項目の細かな説明は不要。
- 推測で問題を追加しない。
- 日本語で2〜3文程度にまとめる。
"""
        )

    if include_proofreading:
        task_rules.append(
            """
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
        )

    summary_schema = (
        '"summary": "Technical SEOのまとめ"'
        if include_summary
        else '"summary": ""'
    )
    proofreading_schema = (
        """
"proofreading": [
  {
    "original": "誤りを含む短い原文",
    "suggestion": "修正案",
    "reason": "誤字・脱字の理由"
  }
]"""
        if include_proofreading
        else '"proofreading": []'
    )

    system_prompt = f"""
あなたはTechnical SEOチェック結果の要約と、日本語本文の誤字脱字確認を担当します。
指定された処理だけを実行してください。

必ず次のJSONオブジェクトだけを返してください。
{{
  {summary_schema},
  {proofreading_schema}
}}

{"".join(task_rules)}
"""

    prompt_sections = [
        f"対象URL:\n{url}",
    ]

    if include_summary:
        prompt_sections.extend(
            [
                "判定件数:\n"
                + json.dumps(status_counts, ensure_ascii=False),
                "全項目の判定:\n"
                + json.dumps(status_rows, ensure_ascii=False),
                "NG・△項目の詳細:\n"
                + json.dumps(issue_rows, ensure_ascii=False),
                "Lighthouse metrics:\n"
                + json.dumps(metrics or {}, ensure_ascii=False),
            ]
        )

    if include_proofreading:
        prompt_sections.append(
            "本文テキスト:\n"
            + (body_text or "本文テキストを取得できず")
        )

    user_prompt = "\n\n".join(prompt_sections)
    max_output_tokens = 700 if include_proofreading else 350

    model_candidates = []
    for candidate in (model, DEFAULT_MODEL, *FALLBACK_MODELS):
        candidate = str(candidate or "").strip()
        if candidate and candidate not in model_candidates:
            model_candidates.append(candidate)

    last_error = None
    tried_models = []

    # High-demand 503s are usually model-specific. Move to another current
    # Flash model quickly instead of waiting through repeated retries on the
    # same overloaded model. This also keeps 30-URL runs from stalling.
    for index, candidate in enumerate(model_candidates):
        tried_models.append(candidate)

        try:
            response = _call_gemini(
                client,
                candidate,
                system_prompt,
                user_prompt,
                max_output_tokens=max_output_tokens,
            )
            summary, proofreading = _parse_response(
                response.text,
                require_summary=include_summary,
                include_proofreading=include_proofreading,
            )
            return {
                "text": summary,
                "proofreading": proofreading,
                "model": candidate,
                "fallback_used": index > 0,
            }
        except Exception as exc:
            last_error = exc

            if not _is_retryable_error(exc):
                # Model aliases can be retired or unavailable for a project.
                # Try the next known model before giving up.
                continue

    # One short delayed retry on the low-cost default helps with brief
    # capacity spikes without multiplying latency across every URL.
    time.sleep(2)
    retry_model = DEFAULT_MODEL
    tried_models.append(f"{retry_model} (retry)")

    try:
        response = _call_gemini(
            client,
            retry_model,
            system_prompt,
            user_prompt,
            max_output_tokens=max_output_tokens,
        )
        summary, proofreading = _parse_response(
            response.text,
            require_summary=include_summary,
            include_proofreading=include_proofreading,
        )
        return {
            "text": summary,
            "proofreading": proofreading,
            "model": retry_model,
            "fallback_used": True,
        }
    except Exception as exc:
        last_error = exc

    raise RuntimeError(
        "Gemini APIから結果を取得できませんでした。"
        f" 試行モデル: {', '.join(tried_models)} / 最終エラー: {last_error}"
    ) from last_error
