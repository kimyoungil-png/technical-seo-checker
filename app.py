import streamlit as st
from siteone_runner import run_siteone

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

        st.info("Unlighthouse は次のステップで接続します。")
