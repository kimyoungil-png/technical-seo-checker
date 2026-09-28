import urllib.error
import urllib.request
import json
import re
from urllib.parse import unquote, urljoin, urlsplit
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36"
)


def inspect_page(url: str, include_body_text: bool = False):
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

    heading_sequence = []
    heading_issues = []
    previous_heading = None

    for tag in soup.find_all(re.compile(r"^h[1-6]$", re.IGNORECASE)):
        level = int(tag.name[1])
        text_value = tag.get_text(" ", strip=True)
        heading_sequence.append({
            "level": level,
            "text": text_value,
        })

        if (
            previous_heading is not None
            and level > previous_heading["level"] + 1
        ):
            skipped = [
                f"H{x}"
                for x in range(
                    previous_heading["level"] + 1,
                    level,
                )
            ]
            heading_issues.append({
                "from_level": previous_heading["level"],
                "from_text": previous_heading["text"],
                "to_level": level,
                "to_text": text_value,
                "skipped": skipped,
            })

        previous_heading = {
            "level": level,
            "text": text_value,
        }

    images = soup.find_all("img")
    def image_src(img):
        attrs = (
            "src",
            "data-src",
            "data-lazy-src",
            "data-original",
            "data-image",
            "data-srcset",
            "srcset",
            "data-desktop-src",
            "data-mobile-src",
            "data-pc-src",
            "data-img-src",
        )

        for attr in attrs:
            value = img.get(attr)
            if not value:
                continue

            if isinstance(value, (list, tuple)):
                value = value[0] if value else ""

            value = str(value).strip()
            if not value:
                continue

            value = value.split(",")[0].strip().split(" ")[0]

            if value.startswith("//"):
                value = "https:" + value

            if value.startswith("data:"):
                continue

            return urljoin(final_url, value)

        picture = img.find_parent("picture")
        if picture is not None:
            for source in picture.find_all("source"):
                value = (
                    source.get("srcset")
                    or source.get("data-srcset")
                    or source.get("data-src")
                    or ""
                )
                if value:
                    value = str(value).split(",")[0].strip().split(" ")[0]
                    if value.startswith("//"):
                        value = "https:" + value
                    return urljoin(final_url, value)

        return ""

    def image_filename(img):
        src = image_src(img)
        if not src:
            return ""

        path = unquote(urlsplit(src).path)
        return path.rstrip("/").split("/")[-1]

    def has_accessible_parent_label(img):
        parent = img.find_parent(["a", "button"])
        if not parent:
            return False

        aria_label = (parent.get("aria-label") or "").strip()
        title_value = (parent.get("title") or "").strip()
        visible_text = parent.get_text(" ", strip=True)

        return bool(aria_label or title_value or visible_text)

    def is_decorative_or_ui_candidate(img):
        if str(img.get("aria-hidden", "")).lower() == "true":
            return True

        if str(img.get("role", "")).lower() in ("presentation", "none"):
            return True

        if has_accessible_parent_label(img):
            return True

        ancestor = img.find_parent(["nav", "header", "footer"])
        if ancestor is not None:
            return True

        src = image_src(img).lower()
        classes = " ".join(img.get("class", [])).lower()

        ui_tokens = (
            "/gnb/",
            "/nav/",
            "/navigation/",
            "icon",
            "logo",
            "sprite",
            "arrow",
            "chevron",
            "lazyload",
        )

        return any(token in src or token in classes for token in ui_tokens)

    content_image_candidates = [
        img
        for img in images
        if not is_decorative_or_ui_candidate(img)
    ]

    missing_alt_priority = [
        img
        for img in content_image_candidates
        if not img.has_attr("alt")
    ]

    missing_alt_examples = []
    for img in missing_alt_priority[:5]:
        missing_alt_examples.append({
            "src": image_src(img),
            "filename": (
                image_filename(img)
                or "画像ファイル名を取得できず"
            ),
            "class": " ".join(img.get("class", [])),
        })

    id_nodes = soup.find_all(attrs={"id": True})
    id_counts = {}
    for node in id_nodes:
        id_value = str(node.get("id", "")).strip()
        if not id_value:
            continue
        id_counts[id_value] = id_counts.get(id_value, 0) + 1

    duplicate_id_examples = [
        {
            "id": id_value,
            "count": count,
        }
        for id_value, count in id_counts.items()
        if count > 1
    ][:5]

    aria_ref_attributes = (
        "aria-labelledby",
        "aria-describedby",
        "aria-controls",
        "aria-owns",
        "aria-activedescendant",
        "aria-details",
        "aria-errormessage",
    )

    broken_aria_references = []
    existing_ids = set(id_counts.keys())

    for node in soup.find_all(True):
        for attr_name in aria_ref_attributes:
            raw_value = node.get(attr_name)
            if not raw_value:
                continue

            for ref_id in str(raw_value).split():
                if ref_id not in existing_ids:
                    node_label = node.name
                    node_id = str(node.get("id", "")).strip()
                    if node_id:
                        node_label += f"#{node_id}"

                    broken_aria_references.append({
                        "element": node_label,
                        "attribute": attr_name,
                        "missing_id": ref_id,
                    })

                    if len(broken_aria_references) >= 5:
                        break

            if len(broken_aria_references) >= 5:
                break

        if len(broken_aria_references) >= 5:
            break

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

    body_text = ""
    if include_body_text:
        content_root = (
            soup.find("main")
            or soup.find("article")
            or soup.body
            or soup
        )
        excluded_text_tags = {
            "script",
            "style",
            "noscript",
            "template",
            "svg",
            "nav",
            "header",
            "footer",
            "form",
            "button",
            "select",
            "option",
        }
        body_text_parts = []

        for text_node in content_root.find_all(string=True):
            parent = text_node.parent
            if parent is None:
                continue

            if getattr(parent, "name", "") in excluded_text_tags:
                continue

            if any(
                getattr(ancestor, "name", "") in excluded_text_tags
                for ancestor in parent.parents
            ):
                continue

            text_value = re.sub(r"\s+", " ", str(text_node)).strip()
            if text_value:
                body_text_parts.append(text_value)

        body_text = "\n".join(body_text_parts).strip()

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
        "heading_sequence": heading_sequence,
        "heading_issues": heading_issues,
        "images_total": len(images),
        "content_image_count": len(content_image_candidates),
        "images_missing_alt_priority": len(missing_alt_priority),
        "images_missing_alt_examples": missing_alt_examples,
        "duplicate_id_examples": duplicate_id_examples,
        "broken_aria_references": broken_aria_references,
        "viewport": viewport,
        "charset": charset,
        "content_type": content_type,
        "hreflang_entries": hreflang_entries,
        "open_graph": open_graph,
        "twitter_card": twitter_card,
        "internal_link_count": len(set(internal_links)),
        "internal_links": sorted(set(internal_links)),
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
        "body_text": body_text,
        "body_text_char_count": len(body_text),
    }
