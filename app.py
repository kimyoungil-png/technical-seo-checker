import streamlit as st

from siteone_runner import run_siteone
from unlighthouse_runner import run_unlighthouse


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

                result_text = (
                    report
                    if report
                    else stdout
                )

                if result_text:
                    with st.expander(
                        "SiteOne Crawler 詳細結果",
                        expanded=False
                    ):
                        st.text(
                            result_text
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

                col1, col2, col3 = (
                    st.columns(3)
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

                st.metric(
                    "TBT",
                    metric_label(
                        metrics.get("tbt")
                    )
                )

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
