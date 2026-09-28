import os
import streamlit as st

from ai_advisor import DEFAULT_MODEL, generate_ai_advice
from page_inspector import inspect_page
from report_builder import build_checks, build_copy_report, counts, html_table
from siteone_runner import run_siteone
from unlighthouse_runner import run_unlighthouse


st.set_page_config(
    page_title="Technical SEO Checker",
    page_icon="🔎",
    layout="wide",
)

st.image("ASCENTSEOLOGO.png", width=360)
st.title("Technical SEO Checker")
st.caption("Ascent SEO Team")

st.write(
    "新規公開・更新した1ページを対象に、Technical SEOを23項目でチェックし、"
    "そのまま共有できる1枚レポートを作成します。"
)

url = st.text_input(
    "チェックするURL",
    placeholder="https://www.example.com/page/",
)

run_lighthouse = st.checkbox(
    "Lighthouse（Performance計測）も実行する",
    value=False,
    help=(
        "Lighthouseはブラウザ計測を伴うため、通常チェックより時間がかかり、"
        "一時的に失敗することがあります。必要なときだけONにしてください。"
    ),
)

generate_ai = st.checkbox(
    "Geminiによる専門レビューを追加する",
    value=True,
)


def get_secret(name):
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name)


if st.button("Technical SEOチェック開始", type="primary"):
    if not url:
        st.warning("URLを入力してください。")
        st.stop()

    if not url.startswith(("http://", "https://")):
        st.warning("http:// または https:// から始まるURLを入力してください。")
        st.stop()

    st.info(f"チェック対象: {url}")

    siteone_text = ""
    siteone_data = {}
    metrics = {}
    lighthouse_status = "skipped"
    lighthouse_error = ""

    total_steps = 3 if run_lighthouse else 2

    with st.spinner(f"1/{total_steps} ページ情報を確認中..."):
        page_data = inspect_page(url)

    with st.spinner(f"2/{total_steps} SiteOne CrawlerでTechnical SEOを確認中..."):
        try:
            siteone_result = run_siteone(url)
            siteone_text = (
                siteone_result.get("report")
                or siteone_result.get("stdout")
                or ""
            )
            siteone_data = siteone_result.get("data") or {}
        except Exception as e:
            st.warning(f"SiteOne Crawlerの一部データを取得できませんでした: {e}")

    if run_lighthouse:
        lighthouse_status = "failed"

        with st.spinner("3/3 LighthouseでPerformanceを確認中..."):
            try:
                unlighthouse_result = run_unlighthouse(url)

                if unlighthouse_result.get("returncode") == 0:
                    metrics = unlighthouse_result.get("metrics") or {}
                    lighthouse_status = "success"
                else:
                    lighthouse_error = (
                        unlighthouse_result.get("stderr")
                        or "Lighthouse API error"
                    )
                    st.warning(
                        "Lighthouse計測を完了できませんでした。"
                        "通常のTechnical SEOチェック結果はそのまま利用できます。"
                    )

            except Exception as e:
                lighthouse_error = str(e)
                st.warning(
                    "Lighthouse計測を完了できませんでした。"
                    "通常のTechnical SEOチェック結果はそのまま利用できます。"
                )
    else:
        st.caption(
            "LighthouseはオプションOFFのため実行していません。"
        )

    checks = build_checks(
        url=url,
        siteone_data=siteone_data,
        page_data=page_data,
        metrics=metrics,
        lighthouse_status=lighthouse_status,
    )

    c = counts(checks)

    st.divider()
    st.header("Technical SEO Check Report")
    st.caption(f"対象URL: {url}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("OK", c["OK"])
    with col2:
        st.metric("△ 要確認", c["△"])
    with col3:
        st.metric("NG 要修正", c["NG"])
    with col4:
        st.metric("— 未実施 / 未取得", c.get("—", 0))

    if c["NG"] == 0:
        st.success(
            "重大なTechnical SEOエラーは検出されませんでした。"
            "△項目は公開意図と照らして確認してください。"
        )
    else:
        st.error(
            f"NGが{c['NG']}件あります。公開・更新後の優先修正対象として確認してください。"
        )

    st.subheader("23項目チェック")
    st.markdown(
        html_table(checks),
        unsafe_allow_html=True,
    )

    ai_text = ""

    if generate_ai:
        st.subheader("Gemini 専門レビュー")

        api_key = get_secret("GEMINI_API_KEY")
        model = get_secret("GEMINI_MODEL") or DEFAULT_MODEL

        if not api_key:
            st.warning(
                "Geminiレビューを利用するには、Streamlit Secretsに"
                "GEMINI_API_KEYを設定してください。"
            )
        else:
            with st.spinner("NG・△項目を中心にGeminiがレビュー中..."):
                try:
                    advice_result = generate_ai_advice(
                        url=url,
                        siteone_text=siteone_text,
                        metrics=metrics,
                        api_key=api_key,
                        model=model,
                        checks=checks,
                    )

                    ai_text = advice_result.get("text", "")
                    st.markdown(ai_text)

                    used_model = advice_result.get("model", model)
                    st.caption(f"Gemini model: {used_model}")

                except Exception as e:
                    st.warning(
                        "Geminiレビューを取得できませんでした。"
                        "23項目チェック結果はそのまま利用できます。"
                    )
                    with st.expander("エラー詳細"):
                        st.code(str(e))

    copy_report = build_copy_report(
        url=url,
        checks=checks,
        ai_text=ai_text,
    )

    st.subheader("コピー用レポート")
    st.write(
        "下記をそのままコピーして、メール・Slack・ドキュメント等に貼り付けられます。"
    )
    st.code(copy_report, language="markdown")

    st.download_button(
        "Markdownレポートを保存",
        data=copy_report,
        file_name="technical-seo-report.md",
        mime="text/markdown",
    )

    with st.expander("詳細データを見る", expanded=False):
        if run_lighthouse:
            st.markdown("#### Lighthouse metrics")
            st.json(metrics)

            if lighthouse_error:
                st.markdown("#### Lighthouse error")
                st.code(lighthouse_error)

        st.markdown("#### Page inspection")
        st.json(page_data)

        st.markdown("#### SiteOne raw report")
        st.text(siteone_text or "No data")
