import urllib.error
import urllib.request
import json
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

    jsonld_scripts = soup.find_all(
        "script",
        attrs={"type": lambda x: x and x.lower() == "application/ld+json"},
    )

    schema_types = []
    schema_errors = []

    def collect_types(value):
        if isinstance(value, dict):
            type_value = value.get("@type")
            if isinstance(type_value, list):
                schema_types.extend(str(v) for v in type_value if v)
            elif type_value:
                schema_types.append(str(type_value))

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

        try:
            parsed_jsonld = json.loads(raw_jsonld)
            collect_types(parsed_jsonld)
        except Exception as exc:
            schema_errors.append(
                f"JSON-LD #{index}: invalid JSON ({exc.__class__.__name__})"
            )

    microdata_items = soup.find_all(attrs={"itemscope": True})
    microdata_types = []
    for item in microdata_items:
        itemtype = item.get("itemtype", "")
        if itemtype:
            microdata_types.append(str(itemtype))

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
        "schema_jsonld_count": len(jsonld_scripts),
        "schema_types": sorted(set(schema_types)),
        "schema_errors": schema_errors,
        "microdata_count": len(microdata_items),
        "microdata_types": sorted(set(microdata_types)),
    }
