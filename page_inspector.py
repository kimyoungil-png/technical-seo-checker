import urllib.error
import urllib.request
import json
import re
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36"
)


def inspect_page(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:
            status = response.getcode()
            final_url = response.geturl()
            headers = dict(response.headers.items())
            raw = response.read(5_000_000)

    except urllib.error.HTTPError as e:
        status = e.code
        final_url = e.geturl()
        headers = dict(e.headers.items()) if e.headers else {}
        raw = e.read(5_000_000)

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }

    html = raw.decode(
        "utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    title = (
        soup.title.get_text(
            " ",
            strip=True,
        )
        if soup.title
        else ""
    )

    description_tag = soup.find(
        "meta",
        attrs={"name": lambda x: x and x.lower() == "description"},
    )
    description = (
        description_tag.get("content", "").strip()
        if description_tag
        else ""
    )

    canonical_tag = soup.find(
        "link",
        attrs={"rel": lambda x: x and "canonical" in [str(v).lower() for v in (x if isinstance(x, list) else [x])]},
    )
    canonical = (
        canonical_tag.get("href", "").strip()
        if canonical_tag
        else ""
    )

    robots_tag = soup.find(
        "meta",
        attrs={"name": lambda x: x and x.lower() == "robots"},
    )
    robots_meta = (
        robots_tag.get("content", "").strip()
        if robots_tag
        else ""
    )

    x_robots_tag = ""
    for key, value in headers.items():
        if key.lower() == "x-robots-tag":
            x_robots_tag = value
            break

    html_tag = soup.find("html")
    lang = (
        html_tag.get("lang", "").strip()
        if html_tag
        else ""
    )

    h1_tags = soup.find_all("h1")
    h1_texts = [
        tag.get_text(
            " ",
            strip=True,
        )
        for tag in h1_tags
    ]

    images = soup.find_all("img")
    missing_alt = [
        img
        for img in images
        if not img.has_attr("alt")
    ]

    viewport_tag = soup.find(
        "meta",
        attrs={"name": lambda x: x and x.lower() == "viewport"},
    )
    viewport = (
        viewport_tag.get("content", "").strip()
        if viewport_tag
        else ""
    )

    charset = ""
    charset_tag = soup.find("meta", attrs={"charset": True})
    if charset_tag:
        charset = str(charset_tag.get("charset", "")).strip()

    content_type = ""
    for key, value in headers.items():
        if key.lower() == "content-type":
            content_type = str(value)
            break

    hreflang_entries = []
    for link in soup.find_all("link"):
        rel_values = link.get("rel") or []
        rel_values = [
            str(v).lower()
            for v in (
                rel_values
                if isinstance(rel_values, list)
                else [rel_values]
            )
        ]
        hreflang = (link.get("hreflang") or "").strip()
        href = (link.get("href") or "").strip()

        if "alternate" in rel_values and hreflang and href:
            hreflang_entries.append({
                "lang": hreflang,
                "href": urljoin(final_url, href),
            })

    def meta_content(*, prop=None, name=None):
        if prop:
            tag = soup.find(
                "meta",
                attrs={"property": lambda x: x and x.lower() == prop.lower()},
            )
        else:
            tag = soup.find(
                "meta",
                attrs={"name": lambda x: x and x.lower() == name.lower()},
            )
        return (tag.get("content", "").strip() if tag else "")

    open_graph = {
        "title": meta_content(prop="og:title"),
        "description": meta_content(prop="og:description"),
        "image": meta_content(prop="og:image"),
        "url": meta_content(prop="og:url"),
        "type": meta_content(prop="og:type"),
    }

    twitter_card = {
        "card": meta_content(name="twitter:card"),
        "title": meta_content(name="twitter:title"),
        "description": meta_content(name="twitter:description"),
        "image": meta_content(name="twitter:image"),
    }

    anchors = soup.find_all("a")
    page_host = urlsplit(final_url).netloc.lower()
    internal_links = []
    invalid_links = []

    for anchor in anchors:
        href = (anchor.get("href") or "").strip()

        if not href:
            invalid_links.append("empty href")
            continue

        lowered = href.lower()
        if lowered.startswith(("javascript:", "mailto:", "tel:", "#")):
            if lowered.startswith("javascript:"):
                invalid_links.append(href)
            continue

        absolute = urljoin(final_url, href)
        parsed_link = urlsplit(absolute)

        if parsed_link.scheme in ("http", "https"):
            if parsed_link.netloc.lower() == page_host:
                internal_links.append(absolute)

    favicon = ""
    for link in soup.find_all("link"):
        rel_values = link.get("rel") or []
        rel_values = [
            str(v).lower()
            for v in (
                rel_values
                if isinstance(rel_values, list)
                else [rel_values]
            )
        ]
        if any("icon" == v or v.endswith("icon") for v in rel_values):
            favicon = urljoin(final_url, (link.get("href") or "").strip())
            if favicon:
                break

    jsonld_scripts = soup.find_all(
        "script",
        attrs={"type": lambda x: x and x.lower() == "application/ld+json"},
    )

    schema_types = []
    schema_entities = []
    schema_errors = []
    breadcrumb_lists = []

    def extract_breadcrumbs(node):
        items = []
        for element in node.get("itemListElement", []) or []:
            if not isinstance(element, dict):
                continue

            position = element.get("position")
            name = element.get("name")
            item_value = element.get("item")

            item_url = ""
            if isinstance(item_value, str):
                item_url = item_value
            elif isinstance(item_value, dict):
                item_url = (
                    item_value.get("@id")
                    or item_value.get("url")
                    or ""
                )
                if not name:
                    name = item_value.get("name")

            items.append({
                "position": position,
                "name": str(name).strip() if name else "",
                "url": str(item_url).strip() if item_url else "",
            })

        if items:
            breadcrumb_lists.append(items)

    def collect_types(value):
        if isinstance(value, dict):
            type_value = value.get("@type")
            name_value = (
                value.get("name")
                or value.get("headline")
                or value.get("title")
            )

            if isinstance(type_value, list):
                for schema_type in type_value:
                    if schema_type:
                        schema_types.append(str(schema_type))
                        schema_entities.append({
                            "type": str(schema_type),
                            "name": str(name_value).strip() if name_value else "",
                        })
            elif type_value:
                schema_types.append(str(type_value))
                schema_entities.append({
                    "type": str(type_value),
                    "name": str(name_value).strip() if name_value else "",
                })

            type_values = (
                type_value
                if isinstance(type_value, list)
                else [type_value]
            )

            if "BreadcrumbList" in type_values:
                extract_breadcrumbs(value)

            graph = value.get("@graph")
            if isinstance(graph, list):
                for node in graph:
                    collect_types(node)

        elif isinstance(value, list):
            for node in value:
                collect_types(node)

    for index, script in enumerate(jsonld_scripts, start=1):
        raw_jsonld = script.string or script.get_text()
        if not raw_jsonld.strip():
            schema_errors.append(f"JSON-LD #{index}: empty")
            continue

        cleaned_jsonld = raw_jsonld.strip()
        cleaned_jsonld = re.sub(
            r"^\\s*<!--|-->\\s*$",
            "",
            cleaned_jsonld,
        ).strip()
        cleaned_jsonld = cleaned_jsonld.replace(
            "/*<![CDATA[*/",
            "",
        ).replace(
            "/*]]>*/",
            "",
        ).strip()
        if cleaned_jsonld.endswith(";"):
            cleaned_jsonld = cleaned_jsonld[:-1].rstrip()

        try:
            parsed_jsonld = json.loads(cleaned_jsonld)
            collect_types(parsed_jsonld)
        except json.JSONDecodeError as exc:
            schema_errors.append(
                f"JSON-LD #{index}: 構文エラー "
                f"(line {exc.lineno}, column {exc.colno})"
            )
        except Exception as exc:
            schema_errors.append(
                f"JSON-LD #{index}: 解析エラー ({exc.__class__.__name__})"
            )

    microdata_items = soup.find_all(attrs={"itemscope": True})
    microdata_types = []
    microdata_breadcrumbs = []

    for item in microdata_items:
        itemtype = item.get("itemtype", "")
        if itemtype:
            microdata_types.append(str(itemtype))

        if str(itemtype).rstrip("/").endswith("/BreadcrumbList"):
            breadcrumb_items = []
            list_items = item.find_all(
                attrs={"itemprop": lambda x: x and "itemListElement" in str(x)}
            )

            for list_item in list_items:
                name_node = list_item.find(
                    attrs={"itemprop": lambda x: x and "name" in str(x)}
                )
                position_node = list_item.find(
                    attrs={"itemprop": lambda x: x and "position" in str(x)}
                )
                item_node = list_item.find(
                    attrs={"itemprop": lambda x: x and "item" in str(x)}
                )

                name = ""
                if name_node:
                    name = (
                        name_node.get("content")
                        or name_node.get_text(" ", strip=True)
                        or ""
                    )

                position = ""
                if position_node:
                    position = (
                        position_node.get("content")
                        or position_node.get("value")
                        or position_node.get_text(" ", strip=True)
                        or ""
                    )

                item_url = ""
                if item_node:
                    item_url = (
                        item_node.get("href")
                        or item_node.get("content")
                        or item_node.get("itemid")
                        or ""
                    )

                breadcrumb_items.append({
                    "position": position,
                    "name": str(name).strip(),
                    "url": urljoin(final_url, str(item_url).strip()) if item_url else "",
                })

            if breadcrumb_items:
                microdata_breadcrumbs.append(breadcrumb_items)

    return {
        "ok": True,
        "status": status,
        "final_url": final_url,
        "headers": headers,
        "title": title,
        "description": description,
        "canonical": canonical,
        "robots_meta": robots_meta,
        "x_robots_tag": x_robots_tag,
        "lang": lang,
        "h1_count": len(h1_tags),
        "h1_texts": h1_texts,
        "images_total": len(images),
        "images_missing_alt": len(missing_alt),
        "viewport": viewport,
        "charset": charset,
        "content_type": content_type,
        "hreflang_entries": hreflang_entries,
        "open_graph": open_graph,
        "twitter_card": twitter_card,
        "internal_link_count": len(set(internal_links)),
        "invalid_link_count": len(invalid_links),
        "favicon": favicon,
        "schema_jsonld_count": len(jsonld_scripts),
        "schema_types": sorted(set(schema_types)),
        "schema_entities": schema_entities,
        "schema_errors": schema_errors,
        "breadcrumb_lists": breadcrumb_lists,
        "microdata_count": len(microdata_items),
        "microdata_types": sorted(set(microdata_types)),
        "microdata_breadcrumbs": microdata_breadcrumbs,
    }
