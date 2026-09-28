import os
import streamlit as st

import re


def _status_icon(value):
    if value is True:
        return "✅"
    if value is False:
        return "⚠️"
    return "—"


def _find_bool(text, positive_patterns, negative_patterns):
    lower = (text or "").lower()

    for pattern in negative_patterns:
        if re.search(pattern, lower, re.IGNORECASE):
            return False

    for pattern in positive_patterns:
        if re.search(pattern, lower, re.IGNORECASE):
            return True

    return None


def parse_siteone_summary(text):
    lower = (text or "").lower()

    status_200 = bool(
        re.search(r"\bstatus(?:\s*code)?\s*[:=]?\s*200\b", lower)
        or re.search(r"\bhttp\s*200\b", lower)
        or re.search(r"\b200\s+ok\b", lower)
    )

    indexable = _find_bool(
        text,
        [
            r"indexable",
            r"no\s+noindex",
            r"not\s+blocked\s+by\s+robots",
        ],
        [
            r"noindex",
            r"not\s+indexable",
            r"blocked\s+by\s+robots",
        ],
    )

    canonical = _find_bool(
        text,
        [
            r"canonical.+(?:ok|valid|self)",
            r"has\s+(?:a\s+)?canonical",
            r"canonical\s+url",
        ],
        [
            r"missing\s+canonical",
            r"no\s+canonical",
            r"multiple\s+canonical",
            r"invalid\s+canonical",
        ],
    )

    meta_description = _find_bool(
        text,
        [
            r"meta\s+description.+(?:ok|valid|present|provided)",
            r"has\s+(?:a\s+)?meta\s+description",
        ],
        [
            r"missing\s+meta\s+description",
            r"no\s+meta\s+description",
            r"empty\s+meta\s+description",
            r"meta\s+description.+(?:too\s+short|too\s+long)",
        ],
    )

    h1 = _find_bool(
        text,
        [
            r"all\s+pages\s+have\s+<h1>\s+heading",
            r"single\s+h1",
            r"h1.+(?:ok|valid|present)",
        ],
        [
            r"without\s+<h1>",
            r"missing\s+h1",
            r"multiple\s+<h1>",
            r"multiple\s+h1",
        ],
    )

    return {
        "status_200": status_200,
        "indexable": indexable,
        "canonical": canonical,
        "meta_description": meta_description,
        "h1": h1,
    }


def render_indexability_summary(siteone_text):
    summary = parse_siteone_summary(siteone_text)

    st.markdown("### Indexability")

    rows = [
        (
            "Status 200",
            summary["status_200"],
            "URLが正常に200レスポンスを返しているか。クロール・インデックスの前提条件です。",
        ),
        (
            "Indexable",
            summary["indexable"],
            "noindexやrobots制御などで検索エンジンのインデックス対象外になっていないかを確認します。",
        ),
        (
            "Canonical",
            summary["canonical"],
            "重複URLがある場合に、検索エンジンへ正規URLを示す指定です。",
        ),
        (
            "Meta Description",
            summary["meta_description"],
            "検索結果の説明文候補です。未設定・空欄・極端な長短は改善対象になります。",
        ),
        (
            "H1",
            summary["h1"],
            "ページの主題を示す主要見出しです。基本的にはページ内容を代表するH1が1つある状態が望ましいです。",
        ),
    ]

    for label, value, meaning in rows:
        if label == "Status 200":
            icon = "✅" if value else "⚠️"
        else:
            icon = _status_icon(value)

        st.markdown(f"**{icon} {label}**")
        st.caption(meaning)


def render_performance_summary(metrics):
    st.markdown("### Performance")

    performance = metrics.get("performance")
    seo = metrics.get("seo")
    lcp = metrics.get("lcp")
    cls = metrics.get("cls")

    st.markdown(f"**{score_label(performance)} Performance**")
    st.caption(
        "ページ表示速度やメインスレッドの負荷などを総合したLighthouseのラボスコアです。"
    )

    st.markdown(f"**{score_label(seo)} SEO**")
    st.caption(
        "Lighthouseが確認できる基本的なSEO実装のスコアです。検索順位そのものを示す値ではありません。"
    )

    lcp_ms = metrics.get("lcpMs")
    lcp_icon = "—"
    if isinstance(lcp_ms, (int, float)):
        lcp_icon = "✅" if lcp_ms <= 2500 else ("⚠️" if lcp_ms <= 4000 else "❌")

    st.markdown(f"**{lcp_icon} LCP {metric_label(lcp)}**")
    st.caption(
        "主要コンテンツが表示されるまでの時間です。画像最適化、サーバー応答、レンダリング遅延の影響を受けます。"
    )

    cls_value = metrics.get("clsValue")
    cls_icon = "—"
    if isinstance(cls_value, (int, float)):
        cls_icon = "✅" if cls_value <= 0.1 else ("⚠️" if cls_value <= 0.25 else "❌")

    st.markdown(f"**{cls_icon} CLS {metric_label(cls)}**")
    st.caption(
        "読み込み中のレイアウトのズレを示します。画像サイズ未指定や後挿入UIなどが主な原因です。"
    )

from siteone_runner import run_siteone
from unlighthouse_runner import run_unlighthouse
from ai_advisor import generate_ai_advice, DEFAULT_MODEL


st.set_page_config(
    page_title="Technical SEO Checker",
    page_icon="🔎",
    layout="wide",
)


# ---------------------------------
# Header
# ---------------------------------

st.image(
    "ASCENTSEOLOGO.png",
    width=380
)

st.title("Technical SEO Checker")
st.caption("Ascent SEO Team")

st.write(
    "SiteOne Crawler と Unlighthouse を利用して、"
    "指定URLのテクニカルSEOをチェックします。"
)

st.divider()


# ---------------------------------
# Input
# ---------------------------------

url = st.text_input(
    "チェックするURL",
    placeholder="https://..."
)

generate_ai = st.checkbox(
    "AIによる改善提案も生成する",
    value=True,
    help=(
        "SiteOneとUnlighthouseの診断結果をGemini APIに送り、"
        "項目の意味・優先度・改善方法を日本語で整理します。"
    ),
)


# ---------------------------------
# Helpers
# ---------------------------------

def score_label(score):
    if score is None:
        return "—"

    if score >= 90:
        return f"✅ {score}"

    if score >= 50:
        return f"⚠️ {score}"

    return f"❌ {score}"


def metric_label(value, fallback="—"):
    if value is None:
        return fallback

    return str(value)


def get_secret(name):
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass

    return os.getenv(name)


def explain_metrics():
    with st.expander(
        "各指標の意味を見る",
        expanded=False
    ):
        st.markdown(
            """
**Performance**  
ページ表示の速さや操作応答性などを総合したLighthouseのラボスコアです。

**SEO**  
Lighthouseが確認できる基本的な検索エンジン向け実装を評価します。検索順位そのもののスコアではありません。

**Accessibility**  
代替テキスト、コントラスト、ラベルなど、アクセシビリティ上の基本実装を評価します。

**Best Practices**  
ブラウザセキュリティやWeb実装上の一般的なベストプラクティスを確認します。

**LCP (Largest Contentful Paint)**  
主要コンテンツが表示されるまでの時間です。大きな画像、ヒーロー領域、サーバー応答などの影響を受けます。

**CLS (Cumulative Layout Shift)**  
読み込み中のレイアウトのズレを示します。画像サイズ未指定、後から挿入されるUIなどが主な原因です。

**FCP (First Contentful Paint)**  
最初のテキストや画像が表示されるまでの時間です。

**TBT (Total Blocking Time)**  
メインスレッドが長時間ブロックされた合計時間です。重いJavaScriptの影響を受けやすい指標です。

※ Lighthouseはラボ環境の測定です。実ユーザーのCore Web VitalsはCrUXやSearch Console等で別途確認します。
"""
        )


# ---------------------------------
# Run
# ---------------------------------

if st.button(
    "SEOチェック開始",
    type="primary"
):

    if not url:
        st.warning("URLを入力してください。")
        st.stop()

    if not url.startswith(
        ("http://", "https://")
    ):
        st.warning(
            "http:// または https:// から始まる"
            "URLを入力してください。"
        )
        st.stop()

    st.info(
        f"チェック対象: {url}"
    )

    siteone_success = False
    unlighthouse_success = False
    siteone_text = ""
    metrics = {}


    # ---------------------------------
    # 1. SiteOne
    # ---------------------------------

    st.subheader(
        "1. SiteOne Crawler"
    )

    with st.spinner(
        "SiteOne Crawlerでチェック中..."
    ):
        try:
            siteone_result = run_siteone(url)

            if (
                siteone_result["returncode"]
                == 0
            ):
                siteone_success = True

                st.success(
                    "SiteOne Crawler 完了"
                )

                report = siteone_result.get(
                    "report",
                    ""
                )

                stdout = siteone_result.get(
                    "stdout",
                    ""
                )

                siteone_text = (
                    report
                    if report
                    else stdout
                )

                if siteone_text:
                    render_indexability_summary(
                        siteone_text
                    )

                    with st.expander(
                        "SiteOne Crawler 詳細結果",
                        expanded=False
                    ):
                        st.text(
                            siteone_text
                        )
                else:
                    st.warning(
                        "SiteOne Crawlerは完了しましたが、"
                        "表示できる結果がありませんでした。"
                    )

            else:
                st.error(
                    "SiteOne Crawlerで"
                    "エラーが発生しました。"
                )

                stderr = siteone_result.get(
                    "stderr",
                    ""
                )

                if stderr:
                    st.code(stderr)

        except Exception as e:
            st.error(
                "SiteOne Crawlerを"
                "実行できませんでした。"
            )
            st.exception(e)


    st.divider()


    # ---------------------------------
    # 2. Unlighthouse
    # ---------------------------------

    st.subheader(
        "2. Unlighthouse"
    )

    with st.spinner(
        "Unlighthouseでチェック中..."
    ):
        try:
            unlighthouse_result = (
                run_unlighthouse(url)
            )

            if (
                unlighthouse_result["returncode"]
                == 0
            ):
                unlighthouse_success = True

                st.success(
                    "Unlighthouse 完了"
                )

                metrics = (
                    unlighthouse_result.get(
                        "metrics",
                        {}
                    )
                )

                render_performance_summary(
                    metrics
                )

                st.markdown(
                    "### Lighthouse Scores"
                )

                col1, col2, col3, col4 = (
                    st.columns(4)
                )

                with col1:
                    st.metric(
                        "Performance",
                        score_label(
                            metrics.get(
                                "performance"
                            )
                        )
                    )

                with col2:
                    st.metric(
                        "SEO",
                        score_label(
                            metrics.get(
                                "seo"
                            )
                        )
                    )

                with col3:
                    st.metric(
                        "Accessibility",
                        score_label(
                            metrics.get(
                                "accessibility"
                            )
                        )
                    )

                with col4:
                    st.metric(
                        "Best Practices",
                        score_label(
                            metrics.get(
                                "bestPractices"
                            )
                        )
                    )

                st.markdown(
                    "### Performance Metrics"
                )

                col1, col2, col3, col4 = (
                    st.columns(4)
                )

                with col1:
                    st.metric(
                        "LCP",
                        metric_label(
                            metrics.get("lcp")
                        )
                    )

                with col2:
                    st.metric(
                        "CLS",
                        metric_label(
                            metrics.get("cls")
                        )
                    )

                with col3:
                    st.metric(
                        "FCP",
                        metric_label(
                            metrics.get("fcp")
                        )
                    )

                with col4:
                    st.metric(
                        "TBT",
                        metric_label(
                            metrics.get("tbt")
                        )
                    )

                explain_metrics()

                with st.expander(
                    "Unlighthouse 生データ",
                    expanded=False
                ):
                    st.json(metrics)

            else:
                st.error(
                    "Unlighthouseで"
                    "エラーが発生しました。"
                )

                stderr = (
                    unlighthouse_result.get(
                        "stderr",
                        ""
                    )
                )

                if stderr:
                    st.code(stderr)

        except Exception as e:
            st.error(
                "Unlighthouseを"
                "実行できませんでした。"
            )
            st.exception(e)


    # ---------------------------------
    # 3. AI advice
    # ---------------------------------

    if generate_ai and (
        siteone_success
        or unlighthouse_success
    ):
        st.divider()
        st.subheader(
            "3. AI改善提案"
        )

        api_key = get_secret(
            "GEMINI_API_KEY"
        )

        model = (
            get_secret("GEMINI_MODEL")
            or DEFAULT_MODEL
        )

        if not api_key:
            st.warning(
                "AI改善提案を利用するには、"
                "StreamlitのSecretsに "
                "OPENAI_API_KEY を設定してください。"
            )
        else:
            with st.spinner(
                "AIが診断結果を分析中..."
            ):
                try:
                    advice_result = generate_ai_advice(
                        url=url,
                        siteone_text=siteone_text,
                        metrics=metrics,
                        api_key=api_key,
                        model=model,
                    )

                    st.markdown(
                        advice_result.get("text", "")
                    )

                    used_model = advice_result.get(
                        "model",
                        model,
                    )

                    if advice_result.get(
                        "fallback_used",
                        False,
                    ):
                        st.info(
                            "Gemini 3.8 Flashが混雑していたため、"
                            "自動的にフォールバックモデルで分析しました。"
                        )

                    st.caption(
                        f"Gemini model: {used_model}"
                    )

                except Exception as e:
                    st.error(
                        "Gemini APIが一時的に混雑しているか、"
                        "応答を取得できませんでした。"
                        "少し時間をおいて再実行してください。"
                    )
                    with st.expander(
                        "エラー詳細",
                        expanded=False
                    ):
                        st.code(str(e))


    st.divider()


    # ---------------------------------
    # Final
    # ---------------------------------

    st.subheader(
        "チェック結果"
    )

    if (
        siteone_success
        and unlighthouse_success
    ):
        st.success(
            "Technical SEOチェックが"
            "正常に終了しました。"
        )

    elif (
        siteone_success
        and not unlighthouse_success
    ):
        st.warning(
            "SiteOne Crawlerは完了しましたが、"
            "Unlighthouseのチェックは"
            "完了していません。"
        )

    elif (
        not siteone_success
        and unlighthouse_success
    ):
        st.warning(
            "Unlighthouseは完了しましたが、"
            "SiteOne Crawlerのチェックは"
            "完了していません。"
        )

    else:
        st.error(
            "SiteOne CrawlerとUnlighthouseの"
            "両方で問題が発生しました。"
        )
