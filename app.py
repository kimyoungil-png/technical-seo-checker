import streamlit as st

from siteone_runner import run_siteone
from unlighthouse_runner import run_unlighthouse


st.set_page_config(
    page_title="Technical SEO Checker",
    page_icon="🔎",
    layout="wide",
)


# ロゴ
st.image("ASCENTSEOLOGO.png", width=380)

# タイトル
st.title("Technical SEO Checker")
st.caption("Ascent SEO Team")

st.write(
    "SiteOne Crawler と Unlighthouse を利用して、"
    "指定URLのテクニカルSEOをチェックします。"
)

st.divider()


# URL入力
url = st.text_input(
    "チェックするURL",
    placeholder="https://..."
)


# ボタンを押した時だけ実行
if st.button("SEOチェック開始", type="primary"):

    if not url:
        st.warning("URLを入力してください。")

    elif not url.startswith(("http://", "https://")):
        st.warning("http:// または https:// から始まるURLを入力してください。")

    else:
        st.info(f"チェック対象: {url}")

        #
        # SiteOne Crawler
        #
        st.subheader("1. SiteOne Crawler")

        with st.spinner("SiteOne Crawlerでチェック中..."):

            try:
                siteone_result = run_siteone(url)

                if siteone_result["returncode"] == 0:

                    st.success("SiteOne Crawler 完了")

                    if siteone_result["report"]:
                        with st.expander(
                            "SiteOne Crawler 詳細結果",
                            expanded=True
                        ):
                            st.text(siteone_result["report"])

                    elif siteone_result["stdout"]:
                        with st.expander(
                            "SiteOne Crawler 詳細結果",
                            expanded=True
                        ):
                            st.text(siteone_result["stdout"])

                    else:
                        st.warning(
                            "SiteOne Crawlerは完了しましたが、"
                            "表示できる結果がありませんでした。"
                        )

                else:
                    st.error(
                        "SiteOne Crawlerでエラーが発生しました。"
                    )

                    if siteone_result["stderr"]:
                        st.code(siteone_result["stderr"])

                    if siteone_result["stdout"]:
                        st.code(siteone_result["stdout"])

            except Exception as e:
                st.error(
                    "SiteOne Crawlerを実行できませんでした。"
                )
                st.exception(e)


        st.divider()


        #
        # Unlighthouse
        #
        st.subheader("2. Unlighthouse")

        with st.spinner("Unlighthouseでチェック中..."):

            try:
                unlighthouse_result = run_unlighthouse(url)

                if unlighthouse_result["returncode"] == 0:

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

                        if unlighthouse_result["stdout"]:
                            st.code(
                                unlighthouse_result["stdout"]
                            )

                else:
                    st.error(
                        "Unlighthouseでエラーが発生しました。"
                    )

                    if unlighthouse_result["stderr"]:
                        st.code(
                            unlighthouse_result["stderr"]
                        )

                    if unlighthouse_result["stdout"]:
                        with st.expander(
                            "Unlighthouseログ",
                            expanded=False
                        ):
                            st.code(
                                unlighthouse_result["stdout"]
                            )

            except Exception as e:
                st.error(
                    "Unlighthouseを実行できませんでした。"
                )
                st.exception(e)


        st.divider()

if unlighthouse_result["returncode"] == 0:
    st.success("Technical SEOチェックが正常に終了しました。")
else:
    st.warning(
        "SiteOne Crawlerは完了しましたが、"
        "Unlighthouseのチェックは完了していません。"
    )
