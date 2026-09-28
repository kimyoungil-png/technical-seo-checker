import urllib.error
import urllib.request
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
    }
