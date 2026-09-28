import os
import streamlit as st

from ai_advisor import DEFAULT_MODEL, generate_ai_advice
from page_inspector import inspect_page
from report_builder import build_checks, build_copy_report, counts, html_table, tsv_table
from siteone_runner import run_siteone
from unlighthouse_runner import run_unlighthouse
from ppt_report import build_ppt_report, build_ppt_report_from_default_template


st.set_page_config(
    page_title="Technical SEO Checker",
    page_icon="🔎",
    layout="wide",
)

st.image("ASCENTSEOLOGO.png", width=360)
st.title("Technical SEO Checker")
st.caption("Ascent SEO Team")
# deploy-refresh-20260928

st.write(
    "新規公開・更新した1ページを対象に、Technical SEOを20項目でチェックし、"
    "LighthouseをONにした場合のみPerformance 3項目を追加します。"
)

url = st.text_input(
    "チェックするURL",
    placeholder="https://www.example.com/page/",
    key="input_url",
)

run_lighthouse = st.checkbox(
    "Lighthouse（Performance計測）も実行する",
    value=False,
    help=(
        "Lighthouseはブラウザ計測を伴うため、通常チェックより時間がかかり、"
        "一時的に失敗することがあります。必要なときだけONにしてください。"
    ),
    key="input_run_lighthouse",
)

generate_ai = st.checkbox(
    "Geminiによるまとめを追加する",
    value=True,
    key="input_generate_ai",
)


def get_secret(name):
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name)


def run_audit(target_url, use_lighthouse, use_ai):
    siteone_text = ""
    siteone_data = {}
    metrics = {}
    lighthouse_status = "skipped"
    lighthouse_error = ""

    total_steps = 3 if use_lighthouse else 2

    with st.spinner(f"1/{total_steps} ページ情報を確認中..."):
        page_data = inspect_page(target_url)

    with st.spinner(f"2/{total_steps} SiteOne CrawlerでTechnical SEOを確認中..."):
        try:
            siteone_result = run_siteone(target_url)
            siteone_text = (
                siteone_result.get("report")
                or siteone_result.get("stdout")
                or ""
            )
            siteone_data = siteone_result.get("data") or {}
        except Exception as e:
            st.warning(f"SiteOne Crawlerの一部データを取得できませんでした: {e}")

    if use_lighthouse:
        lighthouse_status = "failed"

        with st.spinner("3/3 LighthouseでPerformanceを確認中..."):
            try:
                unlighthouse_result = run_unlighthouse(target_url)

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
        st.caption("LighthouseはオプションOFFのため実行していません。")

    checks = build_checks(
        url=target_url,
        siteone_data=siteone_data,
        page_data=page_data,
        metrics=metrics,
        lighthouse_status=lighthouse_status,
    )

    check_count = 23 if use_lighthouse else 20
    ai_text = ""
    ai_model = ""

    if use_ai:
        api_key = get_secret("GEMINI_API_KEY")
        model = get_secret("GEMINI_MODEL") or DEFAULT_MODEL

        if not api_key:
            st.warning(
                "Geminiレビューを利用するには、Streamlit Secretsに"
                "GEMINI_API_KEYを設定してください。"
            )
        else:
            with st.spinner("チェック結果を簡潔にまとめています..."):
                try:
                    advice_result = generate_ai_advice(
                        url=target_url,
                        siteone_text=siteone_text,
                        metrics=metrics,
                        api_key=api_key,
                        model=model,
                        checks=checks,
                    )

                    ai_text = advice_result.get("text", "")
                    ai_model = advice_result.get("model", model)

                except Exception as e:
                    st.warning(
                        "Geminiレビューを取得できませんでした。"
                        f"{check_count}項目チェック結果はそのまま利用できます。"
                    )
                    with st.expander("エラー詳細"):
                        st.code(str(e))

    return {
        "url": target_url,
        "run_lighthouse": use_lighthouse,
        "generate_ai": use_ai,
        "checks": checks,
        "counts": counts(checks),
        "check_count": check_count,
        "ai_text": ai_text,
        "ai_model": ai_model,
        "metrics": metrics,
        "page_data": page_data,
        "siteone_text": siteone_text,
        "lighthouse_error": lighthouse_error,
    }


if st.button("Technical SEOチェック開始", type="primary"):
    if not url:
        st.warning("URLを入力してください。")
        st.stop()

    if not url.startswith(("http://", "https://")):
        st.warning("http:// または https:// から始まるURLを入力してください。")
        st.stop()

    st.session_state.pop("ppt_report", None)
    st.session_state.pop("ppt_error", None)

    st.info(f"チェック対象: {url}")
    st.session_state["audit_result"] = run_audit(
        target_url=url,
        use_lighthouse=run_lighthouse,
        use_ai=generate_ai,
    )


audit = st.session_state.get("audit_result")

if audit:
    checks = audit["checks"]
    c = audit["counts"]
    check_count = audit["check_count"]
    ai_text = audit.get("ai_text", "")
    metrics = audit.get("metrics", {})
    page_data = audit.get("page_data", {})
    siteone_text = audit.get("siteone_text", "")
    lighthouse_error = audit.get("lighthouse_error", "")
    checked_url = audit["url"]

    copy_report = build_copy_report(
        url=checked_url,
        checks=checks,
        ai_text=ai_text,
    )

    excel_paste = tsv_table(checks)

    st.divider()
    st.header("Technical SEO Check Report")
    st.caption(f"対象URL: {checked_url}")

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

    st.subheader(f"{check_count}項目チェック")
    st.markdown(
        html_table(checks),
        unsafe_allow_html=True,
    )

    if audit.get("generate_ai"):
        st.subheader("まとめ")
        if ai_text:
            st.markdown(ai_text)
            if audit.get("ai_model"):
                st.caption(f"Gemini model: {audit['ai_model']}")
        else:
            st.caption("まとめは取得できませんでした。")

    st.subheader("PowerPoint出力")
    st.write(
        "サーバー側テンプレートを使って、現在のチェック結果をPowerPointに出力します。"
    )

    if st.button("PPTを生成", key="generate_ppt_report"):
        st.session_state.pop("ppt_report", None)
        st.session_state.pop("ppt_error", None)

        with st.spinner("モバイル画面を取得してPowerPointを生成中..."):
            try:
                try:
                    ppt_result = build_ppt_report_from_default_template(
                        url=checked_url,
                        checks=checks,
                        summary=ai_text,
                    )
                except RuntimeError as template_error:
                    st.warning(
                        "サーバー側テンプレートを読み込めなかったため、"
                        "簡易レイアウトでPowerPointを生成します。"
                    )
                    st.session_state["ppt_template_warning"] = str(template_error)
                    ppt_result = build_ppt_report(
                        url=checked_url,
                        checks=checks,
                        summary=ai_text,
                    )

                st.session_state["ppt_report"] = ppt_result
                st.success(
                    "PowerPointを生成しました。下のボタンからダウンロードしてください。"
                )

            except Exception as e:
                st.session_state["ppt_error"] = str(e)
                st.error("PowerPointの生成に失敗しました。")

    ppt_result = st.session_state.get("ppt_report")
    if ppt_result:
        st.download_button(
            "PowerPointをダウンロード",
            data=ppt_result["bytes"],
            file_name=ppt_result["filename"],
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "presentationml.presentation"
            ),
            key="download_ppt_report",
        )

    ppt_template_warning = st.session_state.get("ppt_template_warning")
    if ppt_template_warning:
        with st.expander("テンプレート読み込みメモ"):
            st.code(ppt_template_warning)

    ppt_error = st.session_state.get("ppt_error")
    if ppt_error:
        with st.expander("PowerPoint生成エラー詳細"):
            st.code(ppt_error)

    st.subheader("Excel貼り付け用")
    st.write(
        "下記をすべてコピーしてExcelのA1セルに貼り付けると、列ごとのテーブルとして展開されます。"
    )
    st.text_area(
        "Excel貼り付け用（タブ区切り）",
        value=excel_paste,
        height=240,
        label_visibility="collapsed",
    )

    st.download_button(
        "TSVを保存",
        data="\ufeff" + excel_paste,
        file_name="technical-seo-report.tsv",
        mime="text/tab-separated-values",
    )

    st.subheader("共有用テキスト")
    st.write("メール・Slack・ドキュメント向けのMarkdown形式です。")
    st.code(copy_report, language="markdown")

    st.download_button(
        "Markdownレポートを保存",
        data=copy_report,
        file_name="technical-seo-report.md",
        mime="text/markdown",
    )

    with st.expander("詳細データを見る", expanded=False):
        if audit.get("run_lighthouse"):
            st.markdown("#### Lighthouse metrics")
            st.json(metrics)

            if lighthouse_error:
                st.markdown("#### Lighthouse error")
                st.code(lighthouse_error)

        st.markdown("#### Page inspection")
        st.json(page_data)

        st.markdown("#### SiteOne raw report")
        st.text(siteone_text or "No data")
