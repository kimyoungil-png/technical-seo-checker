import streamlit as st

from siteone_runner import run_siteone
from unlighthouse_runner import run_unlighthouse


st.set_page_config(
    page_title="Technical SEO Checker",
    page_icon="🔎",
    layout="wide",
)


# -----------------------------
# Header
# -----------------------------

st.image("ASCENTSEOLOGO.png", width=380)

st.title("Technical SEO Checker")
st.caption("Ascent SEO Team")

st.write(
    "SiteOne Crawler と Unlighthouse を利用して、"
    "指定URLのテクニカルSEOをチェックします。"
)

st.divider()


# -----------------------------
# Input
# -----------------------------

url = st.text_input(
    "チェックするURL",
    placeholder="https://..."
)


# -----------------------------
# Run audit
# -----------------------------

if st.button("SEOチェック開始", type="primary"):

    if not url:
        st.warning("URLを入力してください。")
        st.stop()

    if not url.startswith(("http://", "https://")):
        st.warning(
            "http:// または https:// から始まるURLを入力してください。"
        )
        st.stop()

    st.info(f"チェック対象: {url}")

    siteone_result = None
    unlighthouse_result = None

    siteone_success = False
    unlighthouse_success = False


    # -----------------------------
    # 1. SiteOne Crawler
    # -----------------------------

    st.subheader("1. SiteOne Crawler")

    with st.spinner("SiteOne Crawlerでチェック中..."):

        try:
            siteone_result = run_siteone(url)

            if siteone_result["returncode"] == 0:

                siteone_success = True

                st.success("SiteOne Crawler 完了")

                report = siteone_result.get("report", "")
                stdout = siteone_result.get("stdout", "")

                if report:

                    with st.expander(
                        "SiteOne Crawler 詳細結果",
                        expanded=True
                    ):
                        st.text(report)

                elif stdout:

                    with st.expander(
                        "SiteOne Crawler 詳細結果",
                        expanded=True
                    ):
                        st.text(stdout)

                else:

                    st.warning(
                        "SiteOne Crawlerは完了しましたが、"
                        "表示できる結果がありませんでした。"
                    )

            else:

                st.error(
                    "SiteOne Crawlerでエラーが発生しました。"
                )

                stderr = siteone_result.get("stderr", "")
                stdout = siteone_result.get("stdout", "")

                if stderr:
                    st.code(stderr)

                if stdout:
                    with st.expander(
                        "SiteOne Crawlerログ",
                        expanded=False
                    ):
                        st.code(stdout)

        except Exception as e:

            st.error(
                "SiteOne Crawlerを実行できませんでした。"
            )

            st.exception(e)


    st.divider()


    # -----------------------------
    # 2. Unlighthouse
    # -----------------------------

    st.subheader("2. Unlighthouse")

    with st.spinner("Unlighthouseでチェック中..."):

        try:
            unlighthouse_result = run_unlighthouse(url)

            if unlighthouse_result["returncode"] == 0:

                unlighthouse_success = True

                st.success("Unlighthouse 完了")

                reports = unlighthouse_result.get(
                    "reports",
                    []
                )

                if reports:

                    st.write(
                        f"JSONレポート数: {len(reports)}"
                    )

                    first_report = reports[0]["data"]

                    with st.expander(
                        "Unlighthouse JSON結果",
                        expanded=False
                    ):
                        st.json(first_report)

                else:

                    st.warning(
                        "Unlighthouseは完了しましたが、"
                        "JSONレポートが見つかりませんでした。"
                    )

                    stdout = unlighthouse_result.get(
                        "stdout",
                        ""
                    )

                    if stdout:
                        with st.expander(
                            "Unlighthouseログ",
                            expanded=False
                        ):
                            st.code(stdout)

            else:

                st.error(
                    "Unlighthouseでエラーが発生しました。"
                )

                stderr = unlighthouse_result.get(
                    "stderr",
                    ""
                )

                stdout = unlighthouse_result.get(
                    "stdout",
                    ""
                )

                if stderr:
                    st.code(stderr)

                if stdout:
                    with st.expander(
                        "Unlighthouseログ",
                        expanded=False
                    ):
                        st.code(stdout)

        except Exception as e:

            st.error(
                "Unlighthouseを実行できませんでした。"
            )

            st.exception(e)


    st.divider()


    # -----------------------------
    # Final status
    # -----------------------------

    st.subheader("チェック結果")

    if siteone_success and unlighthouse_success:

        st.success(
            "Technical SEOチェックが正常に終了しました。"
        )

    elif siteone_success and not unlighthouse_success:

        st.warning(
            "SiteOne Crawlerは完了しましたが、"
            "Unlighthouseのチェックは完了していません。"
        )

    elif not siteone_success and unlighthouse_success:

        st.warning(
            "Unlighthouseは完了しましたが、"
            "SiteOne Crawlerのチェックは完了していません。"
        )

    else:

        st.error(
            "SiteOne CrawlerとUnlighthouseの"
            "両方で問題が発生しました。"
        )
