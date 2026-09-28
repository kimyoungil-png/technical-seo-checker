import json
from openai import OpenAI


DEFAULT_MODEL = "gpt-5.6-luna"


def generate_ai_advice(
    url: str,
    siteone_text: str,
    metrics: dict,
    api_key: str,
    model: str = DEFAULT_MODEL,
):
    client = OpenAI(api_key=api_key)

    # APIコストと応答時間を抑えるため、SiteOneログは必要量に制限
    siteone_excerpt = (siteone_text or "")[:16000]

    system_prompt = """
あなたはシニアテクニカルSEOアナリストです。
与えられたSiteOne CrawlerとUnlighthouse/Lighthouseの診断結果だけを根拠に、
日本語で改善提案を作成してください。

ルール:
- 測定結果にない問題を断定しない。
- Lighthouseはラボデータであり、実ユーザーのCore Web Vitalsそのものではないことを必要に応じて明記する。
- SEOへの影響、ユーザー体験への影響、実装難易度を分けて考える。
- 問題がない項目にも「何を意味する指標か」を短く説明する。
- 改善案はWeb担当者・エンジニアが実行できる具体性にする。
- SiteOneの英語ログは必要に応じて日本語で要約する。
- URLや測定値を勝手に変更しない。
- 文章は簡潔にし、同じ内容を繰り返さない。

出力形式:
## 総合所見
2〜4文。

## 優先改善項目
重要度の高い順に、各項目を以下の形で記載。
### 項目名
- 判定: OK / 注意 / 要改善
- 意味:
- 今回の結果:
- 改善方法:
- 改善後の確認方法:

## Lighthouse指標の解説
Performance / SEO / Accessibility / Best Practices / LCP / CLS / FCP / TBT を、
今回の数値と関連付けて簡潔に説明。

## すぐ対応できること
実装負荷が比較的小さいものを最大3件。
"""

    user_prompt = f"""
対象URL:
{url}

Unlighthouse / Lighthouse metrics:
{json.dumps(metrics or {}, ensure_ascii=False, indent=2)}

SiteOne Crawler result:
{siteone_excerpt}
"""

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        max_output_tokens=2200,
    )

    return response.output_text
