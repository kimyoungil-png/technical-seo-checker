import streamlit as st
from siteone_runner import run_siteone
from unlighthouse_runner import run_unlighthouse

st.set_page_config(
    page_title="Technical SEO Checker",
    page_icon="🔎",
    layout="wide",
)

st.image("ASCENTSEOLOGO.png", width=320)

st.title("Technical SEO Checker")
st.caption("Ascent SEO Team")

st.write(
    "SiteOne Crawler と Unlighthouse を利用して、"
    "指定URLのテクニカルSEOをチェックします。"
)

url = st.text_input(
    "チェックするURL",
    placeholder="https://ascentnet.co.jp/..."
)

if st.button("SEOチェック開始", type="primary"):
    if not url:
        st.warning("URLを入力してください.")
    else:
        st.info(f"チェック対象: {url}")

        with st.spinner("SiteOne Crawlerでチェック中..."):
            try:
                result = run_siteone(url)

                if result["returncode"] == 0:
                    st.success("SiteOne Crawler 完了")

                    st.subheader("SiteOne Crawler 結果")

                    if result["report"]:
                        st.text(result["report"])
                    else:
                        st.text(result["stdout"])

                else:
                    st.error("SiteOne Crawlerでエラーが発生しました。")
                    st.code(result["stderr"])

            except Exception as e:
                st.error("SiteOne Crawlerを実行できませんでした。")
                st.exception(e)

with st.spinner("Unlighthouseでチェック中..."):
    try:
        ul_result = run_unlighthouse(url)

        if ul_result["returncode"] == 0:
            st.success("Unlighthouse 完了")

            st.subheader("Unlighthouse 結果")

            if ul_result["reports"]:
                st.write(f"JSONレポート数: {len(ul_result['reports'])}")

                first_report = ul_result["reports"][0]["data"]

                st.json(first_report)
            else:
                st.warning("JSONレポートが見つかりませんでした。")
                st.code(ul_result["stdout"])

        else:
            st.error("Unlighthouseでエラーが発生しました。")
            st.code(ul_result["stderr"])

    except Exception as e:
        st.error("Unlighthouseを実行できませんでした。")
        st.exception(e)
