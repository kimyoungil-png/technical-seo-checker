import base64
import os
import streamlit as st

from ai_advisor import DEFAULT_MODEL, build_fallback_summary, generate_ai_advice
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

try:
    APP_PASSWORD = str(st.secrets.get("APP_PASSWORD") or "4321")
except Exception:
    APP_PASSWORD = os.getenv("APP_PASSWORD", "4321")

if not st.session_state.get("authenticated", False):
    st.title("Technical SEO Checker")

    login_left, login_center, login_right = st.columns([1, 1.2, 1])
    with login_center:
        st.image(
            base64.b64decode("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"),
            width=260,
        )

    with st.form("login_form"):
        entered_password = st.text_input(
            "パスワード",
            type="password",
            key="login_password",
        )
        login_submitted = st.form_submit_button("ログイン")

    if login_submitted:
        if entered_password == APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("パスワードが違います。")

    st.stop()

st.image("ASCENTSEOLOGO.png", width=360)
st.title("Technical SEO Checker")
st.caption("Ascent SEO Team")
# deploy-refresh-20260928-2

st.write(
    "新規公開・更新したページを対象にTechnical SEOをチェックし、"
    "チェック完了後にPowerPointレポートまで自動生成します。"
)

MAX_URLS = 30
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
    height=420,
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

generate_ai_summary = st.checkbox(
    "Geminiによるまとめる",
    value=True,
    key="input_generate_ai_summary",
)

generate_proofreading = st.checkbox(
    "Geminiによる本文の誤字脱字チェックを追加する",
    value=True,
    help=(
        "誤字脱字チェックはSEO判定には含めません。"
        "表示本文が長い場合は先頭8,000文字までを確認します。"
    ),
    key="input_generate_proofreading",
)


def get_secret(name):
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name)


def run_audit(target_url, use_lighthouse, use_ai_summary, use_proofreading):
    siteone_text = ""
    siteone_data = {}
    metrics = {}
    lighthouse_status = "skipped"
    lighthouse_error = ""

    total_steps = 3 if use_lighthouse else 2

    with st.spinner(f"1/{total_steps} ページ情報を確認中... {target_url}"):
        page_data = inspect_page(
            target_url,
            include_body_text=use_proofreading,
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
    ai_fallback_summary = False
    proofreading = []

    if use_ai_summary or use_proofreading:
        api_key = get_secret("GEMINI_API_KEY")
        model = get_secret("GEMINI_MODEL") or DEFAULT_MODEL

        if not api_key:
            ai_error = "GEMINI_API_KEYが設定されていません。"
            if use_ai_summary:
                ai_text = build_fallback_summary(checks)
                ai_fallback_summary = True
            st.warning(
                "Gemini機能を利用するには、Streamlit Secretsに"
                "GEMINI_API_KEYを設定してください。"
            )
        else:
            if use_ai_summary and use_proofreading:
                spinner_text = "まとめ・本文の誤字脱字を確認しています"
            elif use_ai_summary:
                spinner_text = "まとめを生成しています"
            else:
                spinner_text = "本文の誤字脱字を確認しています"

            with st.spinner(f"{spinner_text}... {target_url}"):
                try:
                    advice_result = generate_ai_advice(
                        url=target_url,
                        metrics=metrics,
                        api_key=api_key,
                        model=model,
                        checks=checks,
                        body_text=body_text_for_ai,
                        include_summary=use_ai_summary,
                        include_proofreading=use_proofreading,
                    )
                    if use_ai_summary:
                        ai_text = advice_result.get("text", "")
                    if use_proofreading:
                        proofreading = (
                            advice_result.get("proofreading", [])
                            or []
                        )
                    ai_model = advice_result.get("model", model)
                except Exception as e:
                    ai_error = str(e)
                    if use_ai_summary:
                        ai_text = build_fallback_summary(checks)
                        ai_fallback_summary = True

                    if use_ai_summary and use_proofreading:
                        st.warning(
                            "Gemini APIが一時的に利用できないため、"
                            "まとめはチェック結果から自動生成し、"
                            "本文の誤字脱字チェックは未実施です。"
                        )
                    elif use_ai_summary:
                        st.warning(
                            "Gemini APIが一時的に利用できないため、"
                            "チェック結果から自動生成したまとめを表示します。"
                        )
                    else:
                        st.warning(
                            "Gemini APIが一時的に利用できないため、"
                            "本文の誤字脱字チェックは実施できませんでした。"
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
        "generate_ai_summary": use_ai_summary,
        "generate_proofreading": use_proofreading,
        "checks": checks,
        "counts": counts(checks),
        "check_count": check_count,
        "ai_text": ai_text,
        "ai_model": ai_model,
        "ai_error": ai_error,
        "ai_fallback_summary": ai_fallback_summary,
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
            "summary_enabled": audit.get("generate_ai_summary", False),
            "proofreading": audit.get("proofreading", []),
            "proofreading_enabled": audit.get("generate_proofreading", False),
            "proofreading_error": (
                audit.get("ai_error", "")
                if audit.get("generate_proofreading", False)
                else ""
            ),
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
                    use_ai_summary=generate_ai_summary,
                    use_proofreading=generate_proofreading,
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

    if audit.get("generate_ai_summary"):
        st.subheader("まとめ")
        if ai_text:
            st.markdown(ai_text)
            if audit.get("ai_fallback_summary"):
                st.caption(
                    "Gemini APIが利用できなかったため、"
                    "チェック結果から自動生成した代替まとめです。"
                )
            elif audit.get("ai_model"):
                st.caption(f"Gemini model: {audit['ai_model']}")

            if audit.get("ai_error"):
                with st.expander("Geminiエラー詳細", expanded=False):
                    st.code(audit["ai_error"])
        else:
            st.caption("まとめは取得できませんでした。")

    if audit.get("generate_proofreading"):
        st.subheader("本文の誤字脱字チェック")
        st.caption(
            "SEO判定には含めません。"
            "明確な誤字・脱字・変換ミスだけを確認します。"
        )

        checked_chars = int(
            audit.get("body_text_checked_chars")
            or 0
        )
        total_chars = int(
            audit.get("body_text_char_count")
            or checked_chars
        )
        proofreading = audit.get("proofreading") or []

        if audit.get("ai_error"):
            st.caption(
                "Geminiの取得に失敗したため、"
                "本文チェックは実施できませんでした。"
            )
            if not audit.get("generate_ai_summary"):
                with st.expander("Geminiエラー詳細", expanded=False):
                    st.code(audit["ai_error"])
        elif checked_chars == 0:
            st.caption(
                "本文テキストを取得できなかったため、"
                "誤字脱字チェックは実施していません。"
            )
        elif proofreading:
            for proof_index, item in enumerate(
                proofreading,
                start=1,
            ):
                st.write(
                    f"{proof_index}. 原文: "
                    f"{item.get('original', '')}"
                )
                st.write(
                    f"   修正案: "
                    f"{item.get('suggestion', '')}"
                )
                if item.get("reason"):
                    st.caption(f"理由: {item['reason']}")
        else:
            st.success(
                "明確な誤字脱字は検出されませんでした。"
            )

        if checked_chars and not audit.get("ai_error"):
            if total_chars > checked_chars:
                st.caption(
                    f"本文 {total_chars:,}文字のうち"
                    f"先頭{checked_chars:,}文字を確認しました。"
                )
            else:
                st.caption(
                    f"本文 {checked_chars:,}文字を確認しました。"
                )

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
