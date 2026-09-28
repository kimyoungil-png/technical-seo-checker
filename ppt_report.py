import base64
import io
from copy import deepcopy
import json
import os
import tempfile
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Pt


CLOUD_RUN_SCREENSHOT_API = (
    "https://technical-seo-unlighthouse-api-231228645606."
    "asia-northeast1.run.app/screenshot"
)

PPT_FONT_FACE = "Meiryo UI"
DEFAULT_TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "technical_seo_template.pptx"


def _post_json(api_url: str, payload: dict, timeout: int = 120):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    request = urllib.request.Request(
        api_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"Cloud Run HTTP Error {e.code}: {error_body}"
        ) from e


def _get_mobile_screenshot(url: str) -> bytes:
    data = _post_json(
        CLOUD_RUN_SCREENSHOT_API,
        {"url": url},
        timeout=90,
    )

    if not data.get("success"):
        raise RuntimeError(data.get("error") or "Screenshot failed")

    encoded = data.get("imageBase64")
    if not encoded:
        raise RuntimeError("Screenshot data was not returned")

    return base64.b64decode(encoded)


def _load_server_template_bytes() -> bytes:
    template_path = Path(os.getenv("PPT_TEMPLATE_PATH", str(DEFAULT_TEMPLATE_PATH)))

    if template_path.exists():
        return template_path.read_bytes()

    template_b64 = os.getenv("PPT_TEMPLATE_BASE64", "").strip()
    if template_b64:
        return base64.b64decode(template_b64)

    try:
        from default_ppt_template import DEFAULT_PPT_TEMPLATE_B64

        return base64.b64decode(DEFAULT_PPT_TEMPLATE_B64)
    except Exception:
        pass

    raise RuntimeError(
        "PowerPointテンプレートが見つかりません。"
        " テンプレートをアップロードするか、PPT_TEMPLATE_PATH / PPT_TEMPLATE_BASE64を設定してください。"
    )


def _set_cell_text(cell, text, font_size=6, bold=False, color="000000", align=None):
    cell.text = ""
    paragraph = cell.text_frame.paragraphs[0]
    if align:
        paragraph.alignment = align
    run = paragraph.add_run()
    run.text = str(text or "")
    run.font.name = PPT_FONT_FACE
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)


def _status_color(status: str):
    if status == "OK":
        return "003CFF"
    if status in {"NG", "△"}:
        return "D00000"
    return "555555"


def _replace_title_and_summary(slide, url: str, summary: str):
    parsed = urlparse(url)
    path = parsed.path or "/"
    date_label = f"{datetime.now().month}/{datetime.now().day}"
    title = f"{path}（{date_label}時点チェック）"

    summary = (summary or "").strip()
    if not summary:
        summary = "Technical SEOチェック結果を確認してください。"

    for shape in slide.shapes:
        if not getattr(shape, "has_text_frame", False):
            continue
        if "まとめ" not in shape.text and "URL" not in shape.text:
            continue

        text_frame = shape.text_frame
        text_frame.clear()

        p1 = text_frame.paragraphs[0]
        r1 = p1.add_run()
        r1.text = title
        r1.font.name = PPT_FONT_FACE
        r1.font.size = Pt(14)
        r1.font.bold = True
        r1.font.color.rgb = RGBColor.from_string("222222")

        p2 = text_frame.add_paragraph()
        r2 = p2.add_run()
        r2.text = summary
        r2.font.name = PPT_FONT_FACE
        r2.font.size = Pt(14)
        r2.font.bold = True
        r2.font.color.rgb = RGBColor.from_string("0432FF")
        return


def _fill_table(slide, checks):
    table_shape = next((shape for shape in slide.shapes if getattr(shape, "has_table", False)), None)
    if table_shape is None:
        raise RuntimeError("Template table was not found")

    table = table_shape.table

    _set_cell_text(table.cell(0, 0), "No", 8, True, align=PP_ALIGN.CENTER)
    _set_cell_text(table.cell(0, 1), "チェック項目", 8, True, align=PP_ALIGN.CENTER)
    _set_cell_text(table.cell(0, 2), "", 8, True, align=PP_ALIGN.CENTER)
    _set_cell_text(table.cell(0, 3), "判定", 8, True, align=PP_ALIGN.CENTER)
    _set_cell_text(table.cell(0, 4), "結果", 8, True, align=PP_ALIGN.CENTER)

    max_rows = min(len(checks), len(table.rows) - 1)

    for index in range(max_rows):
        row = checks[index]
        ppt_row = index + 1

        result_text = str(row.get("Result") or "")
        action_text = str(row.get("Action") or "")
        if action_text and action_text != "対応不要":
            result_text += f"\nコメント: {action_text}"

        status = str(row.get("Status") or "")

        _set_cell_text(table.cell(ppt_row, 0), row.get("No"), 7, False, align=PP_ALIGN.CENTER)
        _set_cell_text(table.cell(ppt_row, 1), row.get("Item"), 7, True)
        _set_cell_text(table.cell(ppt_row, 2), row.get("Meaning"), 5, False)
        _set_cell_text(
            table.cell(ppt_row, 3),
            status,
            8,
            True,
            color=_status_color(status),
            align=PP_ALIGN.CENTER,
        )
        _set_cell_text(table.cell(ppt_row, 4), result_text, 7, False)

    for ppt_row in range(max_rows + 1, len(table.rows)):
        for col in range(len(table.columns)):
            table.cell(ppt_row, col).text = ""


def _add_screenshot_behind_phone_frame(slide, screenshot_bytes: bytes):
    phone_shape = next((shape for shape in slide.shapes if shape.shape_type == 13), None)
    if phone_shape is None:
        return

    left = phone_shape.left
    top = phone_shape.top
    width = phone_shape.width
    height = phone_shape.height

    shot_left = left + int(width * 0.09)
    shot_top = top + int(height * 0.06)
    shot_width = int(width * 0.82)
    shot_height = int(height * 0.88)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as image_file:
        image_file.write(screenshot_bytes)
        image_path = image_file.name

    pic = slide.shapes.add_picture(
        image_path,
        shot_left,
        shot_top,
        width=shot_width,
        height=shot_height,
    )

    sp_tree = slide.shapes._spTree
    sp_tree.remove(pic._element)
    sp_tree.insert(2, pic._element)


def _duplicate_template_slide(presentation, source_slide):
    new_slide = presentation.slides.add_slide(source_slide.slide_layout)

    for shape in list(new_slide.shapes):
        element = shape.element
        element.getparent().remove(element)

    for shape in source_slide.shapes:
        cloned = deepcopy(shape.element)
        new_slide.shapes._spTree.insert_element_before(cloned, "p:extLst")

    return new_slide


def build_multi_ppt_report_from_template(reports: list[dict], template_bytes: bytes):
    if not reports:
        raise RuntimeError("PowerPointに出力するレポートがありません。")

    presentation = Presentation(io.BytesIO(template_bytes))
    template_slide = presentation.slides[0]

    while len(presentation.slides) < len(reports):
        _duplicate_template_slide(presentation, template_slide)

    warnings = []

    for index, report in enumerate(reports):
        slide = presentation.slides[index]
        url = str(report.get("url") or "")
        checks = report.get("checks") or []
        summary = str(report.get("summary") or "")

        _replace_title_and_summary(slide, url, summary)
        _fill_table(slide, checks)

        try:
            screenshot = _get_mobile_screenshot(url)
            _add_screenshot_behind_phone_frame(slide, screenshot)
        except Exception as exc:
            warnings.append(f"{url}: モバイルスクリーンショット取得失敗 ({exc})")

    output = io.BytesIO()
    presentation.save(output)
    output.seek(0)

    return {
        "bytes": output.read(),
        "filename": "technical-seo-report.pptx",
        "warnings": warnings,
    }


def build_multi_ppt_report_from_default_template(reports: list[dict]):
    return build_multi_ppt_report_from_template(
        reports=reports,
        template_bytes=_load_server_template_bytes(),
    )
