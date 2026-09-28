import os
import streamlit as st

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
        "SiteOneとUnlighthouseの診断結果をOpenAI APIに送り、"
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
            "OPENAI_API_KEY"
        )

        model = (
            get_secret("OPENAI_MODEL")
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
                    advice = generate_ai_advice(
                        url=url,
                        siteone_text=siteone_text,
                        metrics=metrics,
                        api_key=api_key,
                        model=model,
                    )

                    st.markdown(advice)

                    st.caption(
                        f"AI model: {model}"
                    )

                except Exception as e:
                    st.error(
                        "AI改善提案の生成中に"
                        "エラーが発生しました。"
                    )
                    st.exception(e)


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
