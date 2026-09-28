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
    "Image Alt": "img要素のalt属性を確認します。画像検索・アクセシビリティに必要な代替テキストで、意味のある画像と装飾画像を適切に区別します。",
    "Viewport": "meta viewportを確認します。モバイル端末でのCSS viewportを正しく設定し、レスポンシブレンダリングを成立させる基本要件です。",
    "Schema Markup": "JSON-LD / Microdataの構造化データを検出し、JSON-LDの構文妥当性とSchema.orgの@typeを確認します。Google Rich Results Testの代替ではありません。",
    "BreadcrumbList": "Schema.orgのBreadcrumbListを確認し、階層名・position・リンク先がページのパンくず構造と整合しているかを確認します。",
    "Final URL / Redirect": "入力URLから最終到達URLまでのリダイレクト有無を確認します。公開URL・canonical・内部リンクでURL表記を統一するための確認項目です。",
    "Hreflang": "link rel=alternate hreflangの設定を確認します。言語・地域別URLがあるサイトで検索エンジンへ対応関係を伝える国際SEOシグナルです。",
    "Open Graph": "og:title、og:description、og:image、og:url等のOpen Graphメタデータを確認します。SNS共有時の表示品質とURL整合性を確認します。",
    "Twitter Card": "twitter:card、twitter:title、twitter:description、twitter:image等を確認し、X等で共有された際のカード情報を検証します。",
    "Internal Links": "対象ページ内の内部リンク数とクローラビリティを確認します。通常のhrefを持つ内部リンクはページ発見・サイト構造理解に利用されます。",
    "Charset / Content-Type": "HTTP Content-TypeとHTML charset宣言を確認します。文字コードの不整合はHTML解析・文字化け・メタ情報解釈に影響する可能性があります。",
    "HTML Validity": "DOM構造上の重大なHTML不整合を確認します。壊れたマークアップはレンダリング、アクセシビリティ、クローラ解釈に影響する可能性があります。",
    "SEO Score": "Lighthouse SEOカテゴリの監査スコアです。インデックス可否、リンク、メタ情報、モバイル対応など基礎実装をラボ環境で検査します。順位スコアではありません。",
    "Performance Score": "LighthouseのPerformanceカテゴリ総合スコアです。FCP、LCP、TBT等を基にラボ環境でレンダリング性能を評価します。",
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
            10,
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

    html_item = _summary_item(
        siteone_data,
        "pages-with-invalid-html",
    )
    html_status = _status_from_summary(html_item) or "△"
    checks.append(
        _row(
            14,
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
    internal_status = "OK" if internal_count > 0 and invalid_count == 0 else "△"
    internal_result = (
        f"内部リンク {internal_count}件 / "
        f"javascript等の非クローラブルリンク {invalid_count}件"
    )

    checks.append(
        _row(
            19,
            "その他",
            "Internal Links",
            internal_status,
            internal_result,
            "内部リンクの基本的なクローラビリティを確認します。",
            "主要導線は通常の<a href>で実装してください。javascript:リンクや空hrefがある場合は、検索エンジンが辿れるURLリンクへ変更してください。",
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

    lighthouse_not_run = lighthouse_status == "skipped"
    lighthouse_failed = lighthouse_status == "failed"

    if lighthouse_not_run:
        lighthouse_missing_result = "未実施（オプションOFF）"
    elif lighthouse_failed:
        lighthouse_missing_result = "取得失敗"
    else:
        lighthouse_missing_result = "取得できず"

    seo_score = metrics.get("seo")
    seo_status = (
        "—"
        if seo_score is None
        else (
            "OK"
            if isinstance(seo_score, (int, float)) and seo_score >= 90
            else (
                "△"
                if isinstance(seo_score, (int, float)) and seo_score >= 80
                else "NG"
            )
        )
    )
    checks.append(
        _row(
            21,
            "Lighthouse",
            "SEO Score",
            seo_status,
            str(seo_score) if seo_score is not None else lighthouse_missing_result,
            "Lighthouseが確認できる基本的なSEO実装の総合スコアです。検索順位そのものではありません。",
            "Lighthouse SEO監査の失敗項目を確認し、クロール、メタ情報、リンク、モバイル対応などの基本実装を修正してください。",
        )
    )

    perf = metrics.get("performance")
    perf_status = (
        "—"
        if perf is None
        else (
            "OK"
            if isinstance(perf, (int, float)) and perf >= 90
            else (
                "△"
                if isinstance(perf, (int, float)) and perf >= 50
                else "NG"
            )
        )
    )
    checks.append(
        _row(
            22,
            "Performance",
            "Performance Score",
            perf_status,
            str(perf) if perf is not None else lighthouse_missing_result,
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
        lcp_status = "—"

    checks.append(
        _row(
            23,
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
            24,
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
            25,
            "Performance",
            "TBT",
            tbt_status,
            metrics.get("tbt") or lighthouse_missing_result,
            "メインスレッドが長時間ブロックされた合計時間です。200ms以下を良好の目安とします。",
            "長いJavaScriptタスクを分割し、不要なJS・サードパーティタグを削減または遅延読み込みしてください。",
        )
    )

    if lighthouse_status == "skipped":
        for row in checks:
            if row["No"] >= 21 and row["Status"] == "—":
                row["Action"] = "LighthouseオプションOFFのため判定対象外"
    elif lighthouse_status == "failed":
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
        "| No | 分類 | チェック項目 | 説明 | 判定 | 結果 | 修正コメント |",
        "|---:|---|---|---|:---:|---|---|",
    ]

    for row in checks:
        values = [
            str(row["No"]),
            row["Category"],
            row["Item"],
            row["Meaning"],
            row["Status"],
            row["Result"],
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

        rows.append(
            "<tr>"
            f"<td class='num'>{row['No']}</td>"
            f"<td>{html.escape(str(row['Category']))}</td>"
            f"<td class='item'>{html.escape(str(row['Item']))}</td>"
            f"<td class='desc'>{html.escape(str(row['Meaning']))}</td>"
            f"<td class='judge {status_class}'>{html.escape(str(status))}</td>"
            f"<td>{html.escape(str(row['Result']))}</td>"
            f"<td>{html.escape(str(row['Action']))}</td>"
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
          <th>修正コメント</th>
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
