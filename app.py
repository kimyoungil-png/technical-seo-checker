import streamlit as st

st.set_page_config(
    page_title="Technical SEO Checker",
    page_icon="🔎",
    layout="wide",
)

st.title("Technical SEO Checker")

st.write(
    "SiteOne Crawler と Unlighthouse を利用して、"
    "指定URLのテクニカルSEOをチェックします。"
)

url = st.text_input(
    "チェックするURL",
    placeholder="https://www.samsung.com/jp/..."
)

if st.button("SEOチェック開始", type="primary"):
    if not url:
        st.warning("URLを入力してください。")
    else:
        st.info(f"チェック対象: {url}")
        st.write("SiteOne Crawler: 未接続")
        st.write("Unlighthouse: 未接続")
