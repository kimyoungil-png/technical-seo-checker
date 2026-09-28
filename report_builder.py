from urllib.parse import urljoin, urlsplit, urlunsplit


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



def _broken_internal_links(
    siteone_data,
    page_url,
    internal_links,
    limit=3,
):
    rows = (
        siteone_data.get("tables", {})
        .get("404", {})
        .get("rows", [])
    )

    normalized_internal_links = {
        _normalize_url(link)
        for link in (internal_links or [])
        if link
    }

    broken_urls = []

    for row in rows:
        target = (row.get("url") or "").strip()
        if not target:
            continue

        absolute = urljoin(page_url, target)
        normalized_target = _normalize_url(absolute)

        # SiteOne's 404 table also contains JS/JSON/images and other assets.
        # Count only URLs that actually appeared in an <a href> on this page.
        if normalized_target not in normalized_internal_links:
            continue

        if absolute not in broken_urls:
            broken_urls.append(absolute)

    return {
        "count": len(broken_urls),
        "examples": broken_urls[:limit],
    }


TECHNICAL_MEANINGS = {
    "HTTP Status": "HTTPレスポンスコードを確認し、Googlebot等のクローラが対象URLを正常取得できる状態（200 OK）かを判定します。",
    "HTTPS": "TLSで暗号化されたHTTPS配信かを確認します。HTTPSは通信保護に加え、正規URL・リダイレクト設計の基盤になります。",
    "Indexability": "robots.txt、meta robots、X-Robots-Tagなどのクロール／インデックス制御を確認し、検索エンジンのインデックス対象になれる状態かを判定します。",
    "Canonical": "rel=canonicalの正規化シグナルを確認し、重複URL群の代表URLが実際の最終到達URLと整合しているかを判定します。",
    "Title": "HTML <title>の有無と文字量を確認します。SERPのタイトル候補であり、検索エンジンがページ主題・クエリ関連性を理解する主要なオンページシグナルです。",
    "Meta Description": "meta name=descriptionの有無と文字量を確認します。直接的なランキング要因ではありませんが、SERPスニペット候補としてCTRと検索意図の伝達に関与します。",
    "H1": "最上位見出しH1の有無と個数を確認します。DOM上の見出しアウトラインとページの主題を明確化するセマンティックHTMLの基本要素です。",
    "Heading Structure": "H1→H2→H3の見出し階層を確認し、heading levelのスキップや不自然なアウトラインがないかを判定します。",
    "Lang Attribute": "html要素のlang属性を確認します。文書言語を検索エンジン、ブラウザ、スクリーンリーダーへ明示する国際化・アクセシビリティ上の基本設定です。",
    "Image Alt": "コンテンツ画像候補のみを対象に、alt属性の有無を確認します。ナビゲーション・UI・装飾用途と推定される画像は集計・判定から除外します。",
    "Viewport": "meta viewportを確認します。モバイル端末でのCSS viewportを正しく設定し、レスポンシブレンダリングを成立させる基本要件です。",
    "Schema Markup": "JSON-LD / Microdataの構造化データを検出し、JSON-LDの構文妥当性とSchema.orgの@typeを確認します。Google Rich Results Testの代替ではありません。",
    "BreadcrumbList": "Schema.orgのBreadcrumbListを確認し、階層名・position・リンク先がページのパンくず構造と整合しているかを確認します。",
    "Final URL / Redirect": "入力URLから最終到達URLまでのリダイレクト有無を確認します。公開URL・canonical・内部リンクでURL表記を統一するための確認項目です。",
    "Hreflang": "link rel=alternate hreflangの設定を確認します。言語・地域別URLがあるサイトで検索エンジンへ対応関係を伝える国際SEOシグナルです。",
    "Open Graph": "og:title、og:description、og:image、og:url等のOpen Graphメタデータを確認します。SNS共有時の表示品質とURL整合性を確認します。",
    "Twitter Card": "twitter:card、twitter:title、twitter:description、twitter:image等を確認し、X等で共有された際のカード情報を検証します。",
    "Internal Links": "対象ページ内の内部リンクとリンク切れ（404）を確認します。javascript:等のリンクは参考情報として件数のみ表示し、判定には使用しません。",
    "Charset / Content-Type": "HTTP Content-TypeとHTML charset宣言を確認します。文字コードの不整合はHTML解析・文字化け・メタ情報解釈に影響する可能性があります。",
    "HTML Validity": "DOM構造上の重大なHTML不整合を確認します。壊れたマークアップはレンダリング、アクセシビリティ、クローラ解釈に影響する可能性があります。",
    "LCP": "Largest Contentful Paint。viewport内の主要コンテンツが描画されるまでの時間で、Core Web Vitalsの主要指標です。ラボ値では2.5秒以下を良好の目安とします。",
    "CLS": "Cumulative Layout Shift。ページ表示中の予期しないレイアウトシフト量を示すCore Web Vitals指標で、0.1以下を良好の目安とします。",
    "TBT": "Total Blocking Time。FCP以降にメインスレッドを50ms超ブロックしたLong Taskの超過時間合計で、JavaScript実行負荷の診断に使います。",
}


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
        "Meaning": TECHNICAL_MEANINGS.get(item, meaning),
        "Action": (
            "対応不要"
            if status == "OK"
            else (
                "測定データを取得できていないため、再実行して確認してください。"
                if status == "—"
                else action
            )
        ),
    }


def build_checks(
    url,
    siteone_data,
    page_data,
    metrics,
    lighthouse_status="success",
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
    elif _normalize_url(canonical) == _normalize_url(
        page_data.get("final_url") or url
    ):
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

    title_len = len(title)
    if not title:
        title_status = "NG"
    elif 15 <= title_len <= 70:
        title_status = "OK"
    else:
        title_status = "△"

    checks.append(
        _row(
            5,
            "Meta",
            "Title",
            title_status,
            f"{title} / {title_len}文字" if title else "未設定 / 0文字",
            "Titleを確認します。",
            "Titleが未設定ならページ固有のTitleを追加してください。設定済みでも極端に短い・長い場合は、主要テーマを前半に置きつつ概ね15〜70文字を目安に調整してください。",
        )
    )

    description = (
        page_data.get("description", "")
        if page_data.get("ok")
        else ""
    ) or seo_row.get("description", "")

    desc_len = len(description)
    if not description:
        desc_status = "NG"
    elif 50 <= desc_len <= 180:
        desc_status = "OK"
    else:
        desc_status = "△"

    checks.append(
        _row(
            6,
            "Meta",
            "Meta Description",
            desc_status,
            f"{description} / {desc_len}文字" if description else "未設定 / 0文字",
            "Meta Descriptionを確認します。",
            "未設定ならページ内容と検索意図を要約する固有のdescriptionを追加してください。設定済みでも極端に短い・長い場合は概ね50〜180文字を目安に調整してください。",
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

    h1_status = (
        "OK"
        if h1_count == 1
        else ("NG" if h1_count == 0 else "△")
    )
    h1_texts = page_data.get("h1_texts", []) if page_data.get("ok") else []
    h1_result = f"{h1_count}個"
    if h1_texts:
        h1_result += " / " + " | ".join(h1_texts[:2])

    checks.append(
        _row(
            7,
            "Content Structure",
            "H1",
            h1_status,
            h1_result,
            "ページの主題を示す最上位見出しです。",
            "H1が0件ならページ主題を示すH1を追加してください。複数ある場合は、意図した文書構造か確認し、必要に応じて主見出しを1つに整理してください。",
        )
    )

    direct_heading_issues = page_data.get("heading_issues", [])

    if page_data.get("ok"):
        if direct_heading_issues:
            heading_status = "△"
            examples = []
            for issue in direct_heading_issues[:3]:
                skipped = " / ".join(issue.get("skipped", []))
                examples.append(
                    f"<h{issue.get('from_level')}> "
                    f"{issue.get('from_text') or '（テキストなし）'} → "
                    f"<h{issue.get('to_level')}> "
                    f"{issue.get('to_text') or '（テキストなし）'} "
                    f"（{skipped}をスキップ）"
                )

            heading_text = (
                f"このページで見出し階層のスキップ {len(direct_heading_issues)}件"
                f" / 例: {' | '.join(examples)}"
            )
        else:
            heading_status = "OK"
            heading_text = "このページでは見出し階層のスキップなし"
    else:
        heading_item = _summary_item(
            siteone_data,
            "pages-with-skipped-heading-levels",
        )
        heading_status = _status_from_summary(heading_item) or "—"
        heading_text = (
            heading_item.get("text", "判定情報なし")
            if heading_item
            else "判定情報なし"
        )

    checks.append(
        _row(
            8,
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
            9,
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

    if page_data.get("ok"):
        priority_missing = page_data.get("images_missing_alt_priority", 0)
        content_image_count = page_data.get("content_image_count", 0)

        alt_status = "OK" if priority_missing == 0 else "△"

        alt_result = (
            f"alt未設定 {priority_missing}件 / "
            f"コンテンツ画像 {content_image_count}個"
        )

        alt_examples = page_data.get(
            "images_missing_alt_examples",
            [],
        )

        if alt_examples:
            alt_result += (
                " / 例: "
                + " | ".join(
                    example.get("filename")
                    or example.get("src")
                    or "画像ファイル名を取得できず"
                    for example in alt_examples[:3]
                )
            )
    else:
        alt_item = _summary_item(
            siteone_data,
            "pages-without-image-alt-attributes",
        )
        alt_status = _status_from_summary(alt_item) or "—"
        alt_result = (
            alt_item.get("text", "判定情報なし")
            if alt_item
            else "判定情報なし"
        )

    checks.append(
        _row(
            10,
            "HTML",
            "Image Alt",
            alt_status,
            alt_result,
            "画像の内容を検索エンジンと支援技術へ伝える代替テキストです。",
            "コンテンツ画像候補にaltが未設定の場合は、画像内容を簡潔に説明するaltを設定してください。",
        )
    )

    viewport = (
        page_data.get("viewport", "")
        if page_data.get("ok")
        else ""
    )
    checks.append(
        _row(
            11,
            "Mobile",
            "Viewport",
            "OK" if viewport else "NG",
            viewport or "未設定",
            "モバイル端末でページを適切な幅・倍率で表示するための基本設定です。",
            "head内にmeta viewportを設定し、レスポンシブ表示を確認してください。",
        )
    )

    schema_jsonld_count = page_data.get("schema_jsonld_count", 0)
    schema_microdata_count = page_data.get("microdata_count", 0)
    schema_errors = page_data.get("schema_errors", [])
    schema_types = page_data.get("schema_types", [])
    schema_entities = page_data.get("schema_entities", [])
    microdata_types = page_data.get("microdata_types", [])
    all_schema_types = schema_types + microdata_types
    total_schema = schema_jsonld_count + schema_microdata_count

    if schema_errors and total_schema > 0:
        schema_status = "△"
        schema_result = " / ".join(schema_errors[:2])
    elif schema_errors:
        schema_status = "NG"
        schema_result = " / ".join(schema_errors[:2])
    elif total_schema > 0:
        schema_status = "OK"
        unique_types = []
        for schema_type in all_schema_types:
            if schema_type and schema_type not in unique_types:
                unique_types.append(schema_type)

        type_text = ", ".join(unique_types[:6]) if unique_types else "type未取得"

        itempage_names = []
        for entity in schema_entities:
            if entity.get("type") == "ItemPage":
                name = (entity.get("name") or "").strip()
                if name and name not in itempage_names:
                    itempage_names.append(name)

        itempage_text = ""
        if itempage_names:
            itempage_text = (
                " / ItemPage name: "
                + " | ".join(itempage_names[:3])
            )

        schema_result = (
            f"JSON-LD {schema_jsonld_count}ブロック / "
            f"Microdata {schema_microdata_count}要素 / "
            f"@type {len(unique_types)}種類: {type_text}"
            f"{itempage_text}"
        )
    else:
        schema_status = "△"
        schema_result = "構造化データを検出せず"

    checks.append(
        _row(
            12,
            "Structured Data",
            "Schema Markup",
            schema_status,
            schema_result,
            "構造化データを検証します。",
            "JSON-LDの構文エラーがある場合は修正してください。未実装の場合は、このページがArticle、Product、BreadcrumbList、FAQPage等のSchema.orgマークアップ対象かを確認し、検索機能上のメリットがある場合のみ実装してください。",
        )
    )

    breadcrumb_lists = (
        page_data.get("breadcrumb_lists", [])
        + page_data.get("microdata_breadcrumbs", [])
    )

    if breadcrumb_lists:
        breadcrumb_status = "OK"
        breadcrumb_parts = []

        for breadcrumb in breadcrumb_lists[:2]:
            ordered = sorted(
                breadcrumb,
                key=lambda x: (
                    int(x.get("position"))
                    if str(x.get("position", "")).isdigit()
                    else 999
                ),
            )

            labels = []
            for item in ordered:
                name = (item.get("name") or "").strip()
                position = item.get("position")
                item_url = (item.get("url") or "").strip()

                label = (
                    f"{position}. {name}"
                    if position and name
                    else (name or item_url or "名称不明")
                )

                if item_url:
                    label += f" ({item_url})"

                labels.append(label)

            if labels:
                breadcrumb_parts.append(" → ".join(labels))

        breadcrumb_result = " / ".join(breadcrumb_parts) or "BreadcrumbListを検出"
    else:
        breadcrumb_status = "△"
        breadcrumb_result = "BreadcrumbListを検出せず"

    checks.append(
        _row(
            13,
            "Structured Data",
            "BreadcrumbList",
            breadcrumb_status,
            breadcrumb_result,
            "パンくず構造化データを確認します。",
            "ページにパンくずナビゲーションがある場合はBreadcrumbListを実装し、position・name・item URLが実際の階層と一致するよう修正してください。",
        )
    )

    duplicate_ids = page_data.get("duplicate_id_examples", [])
    broken_aria = page_data.get("broken_aria_references", [])

    if page_data.get("ok"):
        html_issues = []

        for issue in duplicate_ids[:3]:
            html_issues.append(
                f"duplicate id: #{issue.get('id')} "
                f"（{issue.get('count')}回）"
            )

        for issue in broken_aria[:3]:
            html_issues.append(
                f"broken ARIA: <{issue.get('element')}> "
                f"{issue.get('attribute')}=\"{issue.get('missing_id')}\" "
                f"（参照先idなし）"
            )

        if html_issues:
            html_status = "△"
            html_result = (
                f"HTML構造上の要確認 {len(duplicate_ids) + len(broken_aria)}件"
                f" / 例: {' | '.join(html_issues[:3])}"
            )
        else:
            html_item = _summary_item(
                siteone_data,
                "pages-with-invalid-html",
            )

            if html_item and _status_from_summary(html_item) in ("△", "NG"):
                html_status = _status_from_summary(html_item)
                html_result = (
                    html_item.get("text", "HTML構造エラーを検出")
                    + " / 詳細箇所はSiteOne側で特定できず"
                )
            else:
                html_status = "OK"
                html_result = "duplicate id / broken ARIA reference なし"
    else:
        html_item = _summary_item(
            siteone_data,
            "pages-with-invalid-html",
        )
        html_status = _status_from_summary(html_item) or "—"
        html_result = (
            html_item.get("text", "判定情報なし")
            if html_item
            else "判定情報なし"
        )

    checks.append(
        _row(
            14,
            "HTML",
            "HTML Validity",
            html_status,
            html_result,
            "重大なHTML構造エラーがなく、ブラウザやクローラが安定して解釈できるかを確認します。",
            "duplicate idはid値が一意になるよう修正し、broken ARIA referenceはaria-*属性の参照先idが実在するよう修正してください。",
        )
    )

    final_url = page_data.get("final_url") or url
    redirected = _normalize_url(final_url) != _normalize_url(url)
    redirect_status = "△" if redirected else "OK"
    redirect_result = (
        f"{url} → {final_url}"
        if redirected
        else "リダイレクトなし"
    )

    checks.append(
        _row(
            15,
            "その他",
            "Final URL / Redirect",
            redirect_status,
            redirect_result,
            "最終到達URLを確認します。",
            "意図したリダイレクトであれば問題ありません。公開URL、canonical、内部リンク、サイトマップで正規URL表記が統一されているか確認してください。",
        )
    )

    hreflang_entries = page_data.get("hreflang_entries", [])
    if hreflang_entries:
        hreflang_status = "OK"
        hreflang_result = " / ".join(
            f"{item.get('lang')}: {item.get('href')}"
            for item in hreflang_entries[:6]
        )
    else:
        hreflang_status = "—"
        hreflang_result = "設定なし"

    checks.append(
        _row(
            16,
            "その他",
            "Hreflang",
            hreflang_status,
            hreflang_result,
            "言語・地域別URLの対応関係を確認します。",
            "多言語・多地域ページがある場合のみ設定してください。単一言語サイトでは未設定でも問題ありません。",
        )
    )

    open_graph = page_data.get("open_graph", {})
    og_required = ["title", "description", "image"]
    og_present = [key for key in og_required if open_graph.get(key)]
    og_status = "OK" if len(og_present) == len(og_required) else "△"
    og_result = (
        f"{len(og_present)}/{len(og_required)}主要項目設定 "
        f"(title={'有' if open_graph.get('title') else '無'}, "
        f"description={'有' if open_graph.get('description') else '無'}, "
        f"image={'有' if open_graph.get('image') else '無'})"
    )

    checks.append(
        _row(
            17,
            "その他",
            "Open Graph",
            og_status,
            og_result,
            "Open Graphメタデータを確認します。",
            "少なくともog:title、og:description、og:imageを設定し、必要に応じてog:urlもcanonicalと整合させてください。",
        )
    )

    twitter = page_data.get("twitter_card", {})
    twitter_required = ["card", "title", "description", "image"]
    twitter_present = [key for key in twitter_required if twitter.get(key)]
    twitter_status = "OK" if len(twitter_present) == len(twitter_required) else "△"
    twitter_result = (
        f"{len(twitter_present)}/{len(twitter_required)}主要項目設定 "
        f"(card={'有' if twitter.get('card') else '無'}, "
        f"title={'有' if twitter.get('title') else '無'}, "
        f"description={'有' if twitter.get('description') else '無'}, "
        f"image={'有' if twitter.get('image') else '無'})"
    )

    checks.append(
        _row(
            18,
            "その他",
            "Twitter Card",
            twitter_status,
            twitter_result,
            "Twitter Cardメタデータを確認します。",
            "SNS共有を想定する場合はtwitter:card等を設定してください。Open Graphのみで運用する方針の場合は△のままで問題ありません。",
        )
    )

    internal_count = page_data.get("internal_link_count", 0)
    invalid_count = page_data.get("invalid_link_count", 0)

    broken_internal = _broken_internal_links(
        siteone_data,
        page_data.get("final_url") or url,
        page_data.get("internal_links", []),
        limit=3,
    )
    broken_count = broken_internal["count"]

    internal_status = "△" if broken_count > 0 else "OK"

    internal_result = (
        f"内部リンク {internal_count}件 / "
        f"リンク切れ(404) {broken_count}件 / "
        f"javascript等 {invalid_count}件（参考）"
    )

    if broken_internal["examples"]:
        internal_result += (
            " / 例: "
            + " | ".join(broken_internal["examples"])
        )

    checks.append(
        _row(
            19,
            "その他",
            "Internal Links",
            internal_status,
            internal_result,
            "内部リンクとリンク切れを確認します。",
            "404の内部リンクがある場合はリンク先URLを修正・差し替え・削除してください。javascript:等のリンクはこの判定には含めません。",
        )
    )

    charset = page_data.get("charset", "")
    content_type = page_data.get("content_type", "")
    charset_ok = bool(charset) or "charset=" in content_type.lower()
    content_type_ok = "text/html" in content_type.lower()
    charset_status = "OK" if charset_ok and content_type_ok else "△"
    charset_result = (
        f"Content-Type: {content_type or '取得できず'} / "
        f"charset: {charset or 'HTML宣言なし'}"
    )

    checks.append(
        _row(
            20,
            "その他",
            "Charset / Content-Type",
            charset_status,
            charset_result,
            "HTMLレスポンスのMIME typeと文字コード宣言を確認します。",
            "Content-Typeをtext/htmlとして返し、HTTPヘッダーまたはmeta charsetでUTF-8等の文字コードを明示してください。",
        )
    )

    if lighthouse_status == "skipped":
        return checks

    lighthouse_not_run = lighthouse_status == "skipped"
    lighthouse_failed = lighthouse_status == "failed"

    if lighthouse_not_run:
        lighthouse_missing_result = "未実施（オプションOFF）"
    elif lighthouse_failed:
        lighthouse_missing_result = "取得失敗"
    else:
        lighthouse_missing_result = "取得できず"

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
        lcp_status = "—"

    checks.append(
        _row(
            21,
            "Performance",
            "LCP",
            lcp_status,
            metrics.get("lcp") or lighthouse_missing_result,
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
        cls_status = "—"

    checks.append(
        _row(
            22,
            "Performance",
            "CLS",
            cls_status,
            metrics.get("cls") or lighthouse_missing_result,
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
        tbt_status = "—"

    checks.append(
        _row(
            23,
            "Performance",
            "TBT",
            tbt_status,
            metrics.get("tbt") or lighthouse_missing_result,
            "メインスレッドが長時間ブロックされた合計時間です。200ms以下を良好の目安とします。",
            "長いJavaScriptタスクを分割し、不要なJS・サードパーティタグを削減または遅延読み込みしてください。",
        )
    )

    if lighthouse_status == "failed":
        for row in checks:
            if row["No"] >= 21 and row["Status"] == "—":
                row["Action"] = "Lighthouse計測に失敗したため未判定。必要に応じて再実行してください。"

    return checks


def counts(checks):
    return {
        "OK": sum(1 for row in checks if row["Status"] == "OK"),
        "△": sum(1 for row in checks if row["Status"] == "△"),
        "NG": sum(1 for row in checks if row["Status"] == "NG"),
        "—": sum(1 for row in checks if row["Status"] == "—"),
    }


def markdown_table(checks):
    lines = [
        "| No | 分類 | チェック項目 | 説明 | 判定 | 結果 |",
        "|---:|---|---|---|:---:|---|",
    ]

    for row in checks:
        result_text = str(row["Result"])
        action_text = str(row["Action"])

        if action_text and action_text != "対応不要":
            result_text += f" / コメント: {action_text}"

        values = [
            str(row["No"]),
            row["Category"],
            row["Item"],
            row["Meaning"],
            row["Status"],
            result_text,
        ]

        values = [
            str(v).replace("|", "｜").replace("\n", " ")
            for v in values
        ]

        lines.append(
            "| " + " | ".join(values) + " |"
        )

    return "\n".join(lines)


def tsv_table(checks):
    headers = [
        "No",
        "分類",
        "チェック項目",
        "説明",
        "判定",
        "結果",
    ]

    lines = ["\t".join(headers)]

    for row in checks:
        result_text = str(row["Result"])
        action_text = str(row["Action"])

        if action_text and action_text != "対応不要":
            result_text += f" / コメント: {action_text}"

        values = [
            str(row["No"]),
            str(row["Category"]),
            str(row["Item"]),
            str(row["Meaning"]),
            str(row["Status"]),
            result_text,
        ]

        values = [
            value.replace("\t", " ").replace("\n", " ")
            for value in values
        ]

        lines.append("\t".join(values))

    return "\n".join(lines)


def _html_result_text(row):
    import html

    result_text = str(row["Result"])
    action_text = str(row["Action"])

    parts = []

    if " / 例: " in result_text:
        main, examples = result_text.split(" / 例: ", 1)
        parts.append(html.escape(main))

        example_items = [
            item.strip()
            for item in examples.split(" | ")
            if item.strip()
        ]

        if example_items:
            parts.append(
                "<strong>例:</strong><br>"
                + "<br>".join(
                    html.escape(item)
                    for item in example_items
                )
            )
    else:
        parts.append(html.escape(result_text))

    if action_text and action_text != "対応不要":
        parts.append(
            "<strong>コメント:</strong><br>"
            + html.escape(action_text)
        )

    return "<br><br>".join(parts)


def html_table(checks):
    import html

    rows = []
    for row in checks:
        status = row["Status"]
        status_class = {
            "OK": "status-ok",
            "△": "status-warn",
            "NG": "status-ng",
        }.get(status, "")

        result_html = _html_result_text(row)

        rows.append(
            "<tr>"
            f"<td class='num'>{row['No']}</td>"
            f"<td>{html.escape(str(row['Category']))}</td>"
            f"<td class='item'>{html.escape(str(row['Item']))}</td>"
            f"<td class='desc'>{html.escape(str(row['Meaning']))}</td>"
            f"<td class='judge {status_class}'>{html.escape(str(status))}</td>"
            f"<td class='result'>{result_html}</td>"
            "</tr>"
        )

    return """
    <style>
    .seo-report-table-wrap { overflow-x:auto; }
    table.seo-report-table {
        width:100%;
        border-collapse:collapse;
        font-size:14px;
        line-height:1.55;
    }
    .seo-report-table th, .seo-report-table td {
        border:1px solid #e5e7eb;
        padding:10px 12px;
        vertical-align:top;
        text-align:left;
    }
    .seo-report-table th {
        background:#f8fafc;
        font-weight:700;
        white-space:nowrap;
    }
    .seo-report-table .num { text-align:center; width:42px; }
    .seo-report-table .item { font-weight:600; min-width:130px; }
    .seo-report-table .desc {
        font-size:12px;
        line-height:1.45;
        color:#475569;
        min-width:260px;
    }
    .seo-report-table .judge {
        text-align:center;
        font-weight:700;
        white-space:nowrap;
    }
    .seo-report-table .result {
        min-width:360px;
        line-height:1.6;
    }
    .seo-report-table .status-ok { color:#15803d; }
    .seo-report-table .status-warn { color:#a16207; }
    .seo-report-table .status-ng { color:#b91c1c; }
    </style>
    <div class="seo-report-table-wrap">
    <table class="seo-report-table">
      <thead>
        <tr>
          <th>No</th>
          <th>分類</th>
          <th>チェック項目</th>
          <th>説明</th>
          <th>判定</th>
          <th>結果</th>
        </tr>
      </thead>
      <tbody>
    """ + "".join(rows) + """
      </tbody>
    </table>
    </div>
    """


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
        f"- 判定: OK {c['OK']} / △ {c['△']} / NG {c['NG']} / — {c['—']}",
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
