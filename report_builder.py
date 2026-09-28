from urllib.parse import urlsplit, urlunsplit


def _normalize_url(url):
    if not url:
        return ""

    parts = urlsplit(url)
    path = parts.path or "/"

    if path != "/" and path.endswith("/"):
        path = path[:-1]

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            parts.query,
            "",
        )
    )


def _summary_item(siteone_data, code):
    items = (
        siteone_data.get("summary", {})
        .get("items", [])
    )

    for item in items:
        if item.get("aplCode") == code:
            return item

    return None


def _siteone_seo_row(siteone_data):
    rows = (
        siteone_data.get("tables", {})
        .get("seo", {})
        .get("rows", [])
    )

    return rows[0] if rows else {}


def _siteone_status(siteone_data):
    results = siteone_data.get("results", [])

    for result in results:
        if str(result.get("type")) == "1":
            return str(result.get("status", ""))

    if results:
        return str(results[0].get("status", ""))

    return ""


def _status_from_summary(item):
    if not item:
        return None

    status = str(item.get("status", "")).upper()

    if status == "OK":
        return "OK"

    if status == "WARNING":
        return "△"

    if status == "CRITICAL":
        return "NG"

    if status in ("NOTICE", "INFO"):
        return "△"

    return None


def _row(
    no,
    category,
    item,
    status,
    result,
    meaning,
    action,
):
    return {
        "No": no,
        "Category": category,
        "Item": item,
        "Status": status,
        "Result": result,
        "Meaning": meaning,
        "Action": (
            "対応不要"
            if status == "OK"
            else action
        ),
    }


def build_checks(
    url,
    siteone_data,
    page_data,
    metrics,
):
    checks = []
    seo_row = _siteone_seo_row(siteone_data)

    status_code = (
        page_data.get("status")
        if page_data.get("ok")
        else None
    )
    if status_code is None:
        raw_status = _siteone_status(siteone_data)
        status_code = int(raw_status) if raw_status.isdigit() else None

    checks.append(
        _row(
            1,
            "Crawl / Index",
            "HTTP Status",
            "OK" if status_code == 200 else "NG",
            str(status_code) if status_code is not None else "取得できず",
            "公開URLが検索エンジンから正常に取得できるかを確認します。",
            "公開URLが200を返すよう、404・5xx・不要なリダイレクト・サーバー設定を修正してください。",
        )
    )

    is_https = url.lower().startswith("https://")
    checks.append(
        _row(
            2,
            "Crawl / Index",
            "HTTPS",
            "OK" if is_https else "NG",
            "HTTPS" if is_https else "HTTP",
            "ページが暗号化されたHTTPSで配信されているかを確認します。",
            "HTTPSへ移行し、HTTPからHTTPSへ301リダイレクトしてください。",
        )
    )

    robots_meta = (
        page_data.get("robots_meta", "")
        if page_data.get("ok")
        else ""
    )
    x_robots = (
        page_data.get("x_robots_tag", "")
        if page_data.get("ok")
        else ""
    )
    denied = str(
        seo_row.get(
            "deniedByRobotsTxt",
            "false",
        )
    ).lower() == "true"
    robots_index = str(
        seo_row.get(
            "robotsIndex",
            "1",
        )
    )
    noindex = (
        "noindex" in robots_meta.lower()
        or "noindex" in x_robots.lower()
        or robots_index == "0"
    )

    index_status = "NG" if (denied or noindex) else "OK"
    index_result = (
        "robots.txtで拒否"
        if denied
        else (
            "noindex"
            if noindex
            else "Indexable"
        )
    )
    checks.append(
        _row(
            3,
            "Crawl / Index",
            "Indexability",
            index_status,
            index_result,
            "robots.txtやnoindexによって検索結果への登録を妨げていないかを確認します。",
            "公開対象ページであればrobots.txtの拒否、meta robots / X-Robots-Tagのnoindexを解除してください。",
        )
    )

    canonical = (
        page_data.get("canonical", "")
        if page_data.get("ok")
        else ""
    )
    if not canonical:
        canonical_status = "NG"
        canonical_result = "canonicalなし"
    elif _normalize_url(canonical) == _normalize_url(url):
        canonical_status = "OK"
        canonical_result = canonical
    else:
        canonical_status = "△"
        canonical_result = canonical

    checks.append(
        _row(
            4,
            "Crawl / Index",
            "Canonical",
            canonical_status,
            canonical_result,
            "重複URLが存在する場合に、検索エンジンへ正規URLを伝える指定です。",
            "canonicalを設定してください。別URLを指定している場合は、そのURLを正規URLにする意図が正しいか確認してください。",
        )
    )

    title = (
        page_data.get("title", "")
        if page_data.get("ok")
        else ""
    ) or seo_row.get("title", "")
    checks.append(
        _row(
            5,
            "Meta",
            "Title",
            "OK" if title else "NG",
            title or "未設定",
            "検索結果のタイトル候補であり、ページテーマを検索エンジンへ伝える重要要素です。",
            "ページ固有のTitleを設定し、主要テーマとブランド名が自然に伝わる内容にしてください。",
        )
    )

    title_len = len(title)
    if not title:
        title_len_status = "NG"
    elif 15 <= title_len <= 70:
        title_len_status = "OK"
    else:
        title_len_status = "△"

    checks.append(
        _row(
            6,
            "Meta",
            "Title Length",
            title_len_status,
            f"{title_len}文字",
            "Titleが極端に短い・長い場合、テーマが伝わりにくい、または検索結果で省略されやすくなります。",
            "目安として15〜70文字程度に収めつつ、重要語を前半に置き、冗長な文言を削ってください。",
        )
    )

    description = (
        page_data.get("description", "")
        if page_data.get("ok")
        else ""
    ) or seo_row.get("description", "")

    checks.append(
        _row(
            7,
            "Meta",
            "Meta Description",
            "OK" if description else "NG",
            description or "未設定",
            "検索結果の説明文候補です。直接の順位要因ではありませんが、検索結果で内容を伝える役割があります。",
            "ページ内容と検索意図を簡潔に説明する固有のmeta descriptionを設定してください。",
        )
    )

    desc_len = len(description)
    if not description:
        desc_len_status = "NG"
    elif 50 <= desc_len <= 180:
        desc_len_status = "OK"
    else:
        desc_len_status = "△"

    checks.append(
        _row(
            8,
            "Meta",
            "Meta Description Length",
            desc_len_status,
            f"{desc_len}文字",
            "説明文が短すぎると情報不足、長すぎると検索結果で省略される可能性があります。",
            "日本語ページでは内容を優先しつつ、概ね50〜180文字を目安に簡潔に調整してください。",
        )
    )

    h1_count = (
        page_data.get("h1_count")
        if page_data.get("ok")
        else None
    )
    if h1_count is None:
        h1_text = seo_row.get("h1", "")
        h1_count = 1 if h1_text else 0

    checks.append(
        _row(
            9,
            "Content Structure",
            "H1",
            "OK" if h1_count >= 1 else "NG",
            f"{h1_count}個",
            "ページの主題を示す最上位見出しです。",
            "ページ内容を代表するH1を明示してください。",
        )
    )

    checks.append(
        _row(
            10,
            "Content Structure",
            "H1 Count",
            "OK" if h1_count == 1 else "△",
            f"{h1_count}個",
            "H1が複数でも直ちにSEO違反ではありませんが、1ページの主題を明確にする観点で確認します。",
            "意図なく複数H1を使用している場合は、主見出しを1つに整理し、下位見出しをH2/H3へ変更してください。",
        )
    )

    heading_item = _summary_item(
        siteone_data,
        "pages-with-skipped-heading-levels",
    )
    heading_status = _status_from_summary(heading_item)
    if heading_status is None:
        multi_item = _summary_item(
            siteone_data,
            "pages-with-multiple-h1",
        )
        heading_status = _status_from_summary(multi_item) or "△"
        heading_text = (
            multi_item.get("text")
            if multi_item
            else "判定情報なし"
        )
    else:
        heading_text = heading_item.get("text", "")

    checks.append(
        _row(
            11,
            "Content Structure",
            "Heading Structure",
            heading_status,
            heading_text,
            "H1→H2→H3のように見出し階層が論理的に構成されているかを確認します。",
            "見出しレベルの飛びや不自然な階層を修正し、文書構造が順序立つよう整理してください。",
        )
    )

    lang = (
        page_data.get("lang", "")
        if page_data.get("ok")
        else ""
    )
    lang_item = _summary_item(
        siteone_data,
        "pages-without-lang",
    )
    lang_status = (
        "OK"
        if lang
        else (
            _status_from_summary(lang_item)
            or "NG"
        )
    )
    checks.append(
        _row(
            12,
            "HTML",
            "Lang Attribute",
            lang_status,
            lang or (
                lang_item.get("text", "未設定")
                if lang_item
                else "未設定"
            ),
            "HTMLの言語を検索エンジンや支援技術へ伝える属性です。",
            "html要素に日本語ページならlang=\"ja\"など、適切な言語属性を設定してください。",
        )
    )

    alt_item = _summary_item(
        siteone_data,
        "pages-without-image-alt-attributes",
    )
    alt_status = _status_from_summary(alt_item)
    if alt_status is None and page_data.get("ok"):
        missing_alt = page_data.get("images_missing_alt", 0)
        alt_status = "OK" if missing_alt == 0 else "△"
        alt_result = (
            f"alt属性なし {missing_alt} / "
            f"{page_data.get('images_total', 0)}画像"
        )
    else:
        alt_status = alt_status or "△"
        alt_result = (
            alt_item.get("text", "")
            if alt_item
            else "判定情報なし"
        )

    checks.append(
        _row(
            13,
            "HTML",
            "Image Alt",
            alt_status,
            alt_result,
            "画像の内容を検索エンジンと支援技術へ伝える代替テキストです。",
            "意味のある画像には内容を説明するaltを設定し、装飾画像はalt=\"\"として扱ってください。",
        )
    )

    viewport = (
        page_data.get("viewport", "")
        if page_data.get("ok")
        else ""
    )
    checks.append(
        _row(
            14,
            "Mobile",
            "Viewport",
            "OK" if viewport else "NG",
            viewport or "未設定",
            "モバイル端末でページを適切な幅・倍率で表示するための基本設定です。",
            "head内にmeta viewportを設定し、レスポンシブ表示を確認してください。",
        )
    )

    html_item = _summary_item(
        siteone_data,
        "pages-with-invalid-html",
    )
    html_status = _status_from_summary(html_item) or "△"
    checks.append(
        _row(
            15,
            "HTML",
            "HTML Validity",
            html_status,
            (
                html_item.get("text", "")
                if html_item
                else "判定情報なし"
            ),
            "重大なHTML構造エラーがなく、ブラウザやクローラが安定して解釈できるかを確認します。",
            "不正なタグ構造、閉じタグ、入れ子、重複属性などを修正してください。",
        )
    )

    seo_score = metrics.get("seo")
    seo_status = (
        "OK"
        if isinstance(seo_score, (int, float)) and seo_score >= 90
        else (
            "△"
            if isinstance(seo_score, (int, float)) and seo_score >= 80
            else "NG"
        )
    )
    checks.append(
        _row(
            16,
            "Lighthouse",
            "SEO Score",
            seo_status,
            str(seo_score) if seo_score is not None else "取得できず",
            "Lighthouseが確認できる基本的なSEO実装の総合スコアです。検索順位そのものではありません。",
            "Lighthouse SEO監査の失敗項目を確認し、クロール、メタ情報、リンク、モバイル対応などの基本実装を修正してください。",
        )
    )

    perf = metrics.get("performance")
    perf_status = (
        "OK"
        if isinstance(perf, (int, float)) and perf >= 90
        else (
            "△"
            if isinstance(perf, (int, float)) and perf >= 50
            else "NG"
        )
    )
    checks.append(
        _row(
            17,
            "Performance",
            "Performance Score",
            perf_status,
            str(perf) if perf is not None else "取得できず",
            "Lighthouseのラボ環境で、表示速度やメインスレッド負荷を総合評価したスコアです。",
            "LCP、TBTなど低下要因を優先し、画像、JavaScript、CSS、サーバー応答を改善してください。",
        )
    )

    lcp_ms = metrics.get("lcpMs")
    if isinstance(lcp_ms, (int, float)):
        lcp_status = (
            "OK"
            if lcp_ms <= 2500
            else (
                "△"
                if lcp_ms <= 4000
                else "NG"
            )
        )
    else:
        lcp_status = "△"

    checks.append(
        _row(
            18,
            "Performance",
            "LCP",
            lcp_status,
            metrics.get("lcp") or "取得できず",
            "主要コンテンツが表示されるまでの時間です。2.5秒以下を良好の目安とします。",
            "LCP対象画像の圧縮・preload、不要なレンダーブロック削減、サーバー応答改善を優先してください。",
        )
    )

    cls_value = metrics.get("clsValue")
    if isinstance(cls_value, (int, float)):
        cls_status = (
            "OK"
            if cls_value <= 0.1
            else (
                "△"
                if cls_value <= 0.25
                else "NG"
            )
        )
    else:
        cls_status = "△"

    checks.append(
        _row(
            19,
            "Performance",
            "CLS",
            cls_status,
            metrics.get("cls") or "取得できず",
            "読み込み中のレイアウトのズレを表す指標です。0.1以下を良好の目安とします。",
            "画像・広告・埋め込み領域にサイズを確保し、後挿入コンテンツやWebフォントによるズレを抑えてください。",
        )
    )

    tbt_ms = metrics.get("tbtMs")
    if isinstance(tbt_ms, (int, float)):
        tbt_status = (
            "OK"
            if tbt_ms <= 200
            else (
                "△"
                if tbt_ms <= 600
                else "NG"
            )
        )
    else:
        tbt_status = "△"

    checks.append(
        _row(
            20,
            "Performance",
            "TBT",
            tbt_status,
            metrics.get("tbt") or "取得できず",
            "メインスレッドが長時間ブロックされた合計時間です。200ms以下を良好の目安とします。",
            "長いJavaScriptタスクを分割し、不要なJS・サードパーティタグを削減または遅延読み込みしてください。",
        )
    )

    return checks


def counts(checks):
    return {
        "OK": sum(1 for row in checks if row["Status"] == "OK"),
        "△": sum(1 for row in checks if row["Status"] == "△"),
        "NG": sum(1 for row in checks if row["Status"] == "NG"),
    }


def markdown_table(checks):
    lines = [
        "| No | 分類 | チェック項目 | 判定 | 結果 | 項目の意味 | 修正コメント |",
        "|---:|---|---|:---:|---|---|---|",
    ]

    for row in checks:
        values = [
            str(row["No"]),
            row["Category"],
            row["Item"],
            row["Status"],
            row["Result"],
            row["Meaning"],
            row["Action"],
        ]

        values = [
            str(v).replace("|", "｜").replace("\n", " ")
            for v in values
        ]

        lines.append(
            "| " + " | ".join(values) + " |"
        )

    return "\n".join(lines)


def build_copy_report(
    url,
    checks,
    ai_text="",
):
    c = counts(checks)

    report = [
        "# Technical SEO Check Report",
        "",
        f"- URL: {url}",
        f"- 判定: OK {c['OK']} / △ {c['△']} / NG {c['NG']}",
        "",
        "## チェック結果",
        "",
        markdown_table(checks),
    ]

    if ai_text:
        report += [
            "",
            "## AI所見",
            "",
            ai_text.strip(),
        ]

    return "\n".join(report)
