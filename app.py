import os
import streamlit as st

from ai_advisor import DEFAULT_MODEL, generate_ai_advice
from page_inspector import inspect_page
from report_builder import build_checks, build_copy_report, counts, html_table, tsv_table
from siteone_runner import run_siteone
from unlighthouse_runner import run_unlighthouse
from ppt_report import build_multi_ppt_report_from_default_template


st.set_page_config(
    page_title="Technical SEO Checker",
    page_icon="🔎",
    layout="wide",
)

st.image("ASCENTSEOLOGO.png", width=360)
st.title("Technical SEO Checker")
st.caption("Ascent SEO Team")
# deploy-refresh-20260928-2

st.write(
    "新規公開・更新したページを対象にTechnical SEOをチェックし、"
    "チェック完了後にPowerPointレポートまで自動生成します。"
)

MAX_URLS = 10
SITEONE_DETAIL_CHAR_LIMIT = 50_000
PAGE_DETAIL_LIST_LIMIT = 100
BODY_PROOFREAD_CHAR_LIMIT = 8_000

urls_text = st.text_area(
    f"チェックするURL（1行に1URL、最大{MAX_URLS}件）",
    placeholder=(
        "https://www.example.com/page-1/\n"
        "https://www.example.com/page-2/"
    ),
    key="input_urls",
    height=220,
)

entered_urls = [line.strip() for line in urls_text.splitlines() if line.strip()]
urls = list(dict.fromkeys(entered_urls))
duplicate_url_count = len(entered_urls) - len(urls)

if duplicate_url_count:
    st.caption(f"重複URL {duplicate_url_count}件は1回だけチェックします。")

run_lighthouse = st.checkbox(
    "Lighthouse（Performance計測）も実行する",
    value=False,
    help=(
        "Lighthouseはブラウザ計測を伴うため時間がかかります。"
        "複数URLでは利用できません。"
    ),
    key="input_run_lighthouse",
)

generate_ai = st.checkbox(
    "Geminiによるまとめ・本文の誤字脱字チェックを追加する",
    value=True,
    help=(
        "誤字脱字チェックはSEO判定には含めません。"
        "表示本文が長い場合は先頭8,000文字までを確認します。"
    ),
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

    with st.spinner(f"1/{total_steps} ページ情報を確認中... {target_url}"):
        page_data = inspect_page(
            target_url,
            include_body_text=use_ai,
        )

    body_text = str(page_data.pop("body_text", "") or "")
    body_text_char_count = int(
        page_data.get("body_text_char_count")
        or len(body_text)
    )
    body_text_for_ai = body_text[:BODY_PROOFREAD_CHAR_LIMIT]

    with st.spinner(f"2/{total_steps} SiteOne CrawlerでTechnical SEOを確認中... {target_url}"):
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
        with st.spinner(f"3/3 LighthouseでPerformanceを確認中... {target_url}"):
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
                    st.warning("Lighthouse計測を完了できませんでした。")
            except Exception as e:
                lighthouse_error = str(e)
                st.warning("Lighthouse計測を完了できませんでした。")
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
    ai_error = ""
    proofreading = []

    if use_ai:
        api_key = get_secret("GEMINI_API_KEY")
        model = get_secret("GEMINI_MODEL") or DEFAULT_MODEL

        if not api_key:
            st.warning(
                "Geminiまとめを利用するには、Streamlit Secretsに"
                "GEMINI_API_KEYを設定してください。"
            )
        else:
            with st.spinner(f"まとめ・本文の誤字脱字を確認しています... {target_url}"):
                try:
                    advice_result = generate_ai_advice(
                        url=target_url,
                        metrics=metrics,
                        api_key=api_key,
                        model=model,
                        checks=checks,
                        body_text=body_text_for_ai,
                    )
                    ai_text = advice_result.get("text", "")
                    proofreading = advice_result.get("proofreading", []) or []
                    ai_model = advice_result.get("model", model)
                except Exception as e:
                    ai_error = str(e)
                    st.warning(
                        "Geminiまとめを取得できませんでした。"
                        f"{check_count}項目チェック結果はそのまま利用できます。"
                    )

    page_data_for_ui = dict(page_data)
    internal_links = page_data_for_ui.get("internal_links")
    if isinstance(internal_links, list) and len(internal_links) > PAGE_DETAIL_LIST_LIMIT:
        page_data_for_ui["internal_links"] = internal_links[:PAGE_DETAIL_LIST_LIMIT]
        page_data_for_ui["internal_links_truncated"] = (
            f"{len(internal_links) - PAGE_DETAIL_LIST_LIMIT}件を省略"
        )

    if len(siteone_text) > SITEONE_DETAIL_CHAR_LIMIT:
        siteone_text = (
            siteone_text[:SITEONE_DETAIL_CHAR_LIMIT]
            + "\n... (詳細表示用データを省略)"
        )

    return {
        "url": target_url,
        "run_lighthouse": use_lighthouse,
        "generate_ai": use_ai,
        "checks": checks,
        "counts": counts(checks),
        "check_count": check_count,
        "ai_text": ai_text,
        "ai_model": ai_model,
        "ai_error": ai_error,
        "proofreading": proofreading,
        "body_text_char_count": body_text_char_count,
        "body_text_checked_chars": len(body_text_for_ai),
        "metrics": metrics,
        "page_data": page_data_for_ui,
        "siteone_text": siteone_text,
        "lighthouse_error": lighthouse_error,
    }


def build_ppt_for_audits(audits):
    report_payload = [
        {
            "url": audit["url"],
            "checks": audit["checks"],
            "summary": audit.get("ai_text", ""),
        }
        for audit in audits
    ]

    return build_multi_ppt_report_from_default_template(
        reports=report_payload,
    )


if st.button("Technical SEOチェック開始", type="primary"):
    if len(urls) > MAX_URLS:
        st.error(f"URLは最大{MAX_URLS}件まで入力できます。")
        st.stop()

    if run_lighthouse and len(urls) > 1:
        st.error(
            "LighthouseをONにした場合は、複数URLをチェックできません。"
            "LighthouseをOFFにするか、URLを1件だけ入力してください。"
        )
        st.stop()

    if not urls:
        st.warning("URLを入力してください。")
        st.stop()

    invalid_urls = [
        item for item in urls if not item.startswith(("http://", "https://"))
    ]
    if invalid_urls:
        st.warning("すべてのURLを http:// または https:// から始めてください。")
        st.stop()

    for key in ("ppt_report", "ppt_error", "audit_results", "audit_errors"):
        st.session_state.pop(key, None)

    audit_results = []
    audit_errors = []
    progress = st.progress(0, text=f"0/{len(urls)} URLをチェック中...")

    for index, target_url in enumerate(urls, start=1):
        st.info(f"[{index}/{len(urls)}] チェック対象: {target_url}")
        try:
            audit_results.append(
                run_audit(
                    target_url=target_url,
                    use_lighthouse=run_lighthouse,
                    use_ai=generate_ai,
                )
            )
        except Exception as e:
            audit_errors.append({"url": target_url, "error": str(e)})
            st.warning(
                f"{target_url} のチェックを完了できませんでした。残りのURLは続けて処理します。"
            )

        progress.progress(
            index / len(urls),
            text=f"{index}/{len(urls)} URLのチェックが完了しました。",
        )

    st.session_state["audit_results"] = audit_results
    st.session_state["audit_errors"] = audit_errors

    if not audit_results:
        st.error("チェックを完了できたURLがありませんでした。")
        st.stop()

    with st.spinner(f"{len(audit_results)}ページのPowerPointを自動生成中..."):
        try:
            ppt_result = build_ppt_for_audits(audit_results)
            st.session_state["ppt_report"] = ppt_result
            st.success(f"{len(audit_results)}ページのPowerPointを生成しました。")
            for warning in ppt_result.get("warnings", []):
                st.warning(warning)
        except Exception as e:
            st.session_state["ppt_error"] = str(e)
            st.error("PowerPointの自動生成に失敗しました。")


def render_audit_result(audit, index):
    checks = audit["checks"]
    c = audit["counts"]
    check_count = audit["check_count"]
    ai_text = audit.get("ai_text", "")
    metrics = audit.get("metrics", {})
    page_data = audit.get("page_data", {})
    siteone_text = audit.get("siteone_text", "")
    lighthouse_error = audit.get("lighthouse_error", "")
    checked_url = audit["url"]

    copy_report = build_copy_report(url=checked_url, checks=checks, ai_text=ai_text)
    excel_paste = tsv_table(checks)

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

    with st.expander(f"{check_count}項目チェック", expanded=False):
        st.markdown(html_table(checks), unsafe_allow_html=True)

    if audit.get("generate_ai"):
        st.subheader("まとめ")
        if ai_text:
            st.markdown(ai_text)
            if audit.get("ai_model"):
                st.caption(f"Gemini model: {audit['ai_model']}")
        else:
            st.caption("まとめは取得できませんでした。")
            if audit.get("ai_error"):
                with st.expander("Geminiエラー詳細", expanded=False):
                    st.code(audit["ai_error"])

        st.subheader("本文の誤字脱字チェック")
        st.caption("SEO判定には含めません。明確な誤字・脱字・変換ミスだけを確認します。")

        checked_chars = int(audit.get("body_text_checked_chars") or 0)
        total_chars = int(audit.get("body_text_char_count") or checked_chars)
        proofreading = audit.get("proofreading") or []

        if audit.get("ai_error"):
            st.caption("Geminiの取得に失敗したため、本文チェックも実施できませんでした。")
        elif checked_chars == 0:
            st.caption("本文テキストを取得できなかったため、誤字脱字チェックは実施していません。")
        elif proofreading:
            for proof_index, item in enumerate(proofreading, start=1):
                st.write(f"{proof_index}. 原文: {item.get('original', '')}")
                st.write(f"   修正案: {item.get('suggestion', '')}")
                if item.get("reason"):
                    st.caption(f"理由: {item['reason']}")
        else:
            st.success("明確な誤字脱字は検出されませんでした。")

        if checked_chars:
            if total_chars > checked_chars:
                st.caption(
                    f"本文 {total_chars:,}文字のうち先頭{checked_chars:,}文字を確認しました。"
                )
            else:
                st.caption(f"本文 {checked_chars:,}文字を確認しました。")

    with st.expander("Excel貼り付け用", expanded=False):
        st.write(
            "下記をすべてコピーしてExcelのA1セルに貼り付けると、列ごとのテーブルとして展開されます。"
        )
        st.text_area(
            "Excel貼り付け用（タブ区切り）",
            value=excel_paste,
            height=220,
            label_visibility="collapsed",
            key=f"excel_text_{index}",
        )
        st.download_button(
            "TSVを保存",
            data="\ufeff" + excel_paste,
            file_name=f"technical-seo-report-{index}.tsv",
            mime="text/tab-separated-values",
            key=f"download_tsv_{index}",
        )

    with st.expander("共有用テキスト", expanded=False):
        st.code(copy_report, language="markdown")
        st.download_button(
            "Markdownレポートを保存",
            data=copy_report,
            file_name=f"technical-seo-report-{index}.md",
            mime="text/markdown",
            key=f"download_md_{index}",
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


audits = st.session_state.get("audit_results", [])

if audits:
    st.divider()
    st.header("Technical SEO Check Report")

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
            key="download_ppt_report_top",
        )

    ppt_error = st.session_state.get("ppt_error")
    if ppt_error:
        with st.expander("PowerPoint生成エラー詳細", expanded=True):
            st.code(ppt_error)

    if len(audits) == 1:
        render_audit_result(audits[0], 1)
    else:
        tabs = st.tabs(
            [f"{index}. {audit['url']}" for index, audit in enumerate(audits, start=1)]
        )
        for index, (tab, audit) in enumerate(zip(tabs, audits), start=1):
            with tab:
                render_audit_result(audit, index)

    audit_errors = st.session_state.get("audit_errors", [])
    if audit_errors:
        with st.expander(f"チェック失敗 {len(audit_errors)}件", expanded=False):
            for error in audit_errors:
                st.write(f"{error['url']}: {error['error']}")

    st.subheader("PowerPoint再生成")
    st.write("固定テンプレートを使って、同じ内容を再生成できます。")
    if st.button("PPTを再生成", key="regenerate_ppt_report"):
        with st.spinner(f"{len(audits)}ページのPowerPointを再生成中..."):
            try:
                ppt_result = build_ppt_for_audits(audits)
                st.session_state["ppt_report"] = ppt_result
                st.success(f"{len(audits)}ページのPowerPointを再生成しました。")
            except Exception as e:
                st.session_state["ppt_error"] = str(e)
                st.error("PowerPointの再生成に失敗しました。")
