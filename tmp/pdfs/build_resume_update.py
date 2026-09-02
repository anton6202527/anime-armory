from __future__ import annotations

import copy
from io import BytesIO
from pathlib import Path

from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import ContentStream, FloatObject, NameObject, RectangleObject
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


SOURCE = Path("/Users/wesley/Desktop/jack-前端.pdf")
OUTPUT = Path("/Users/wesley/learn/anime-armory/output/pdf/jack-前端-更新工作经历.pdf")

SHIFT = 36.96
MOVABLE_TOP = 350.0
MOVABLE_BOTTOM = 780.0

REGULAR_FONT = "/System/Library/Fonts/STHeiti Light.ttc"
BOLD_FONT = "/System/Library/Fonts/STHeiti Medium.ttc"


def move_page_content(page: PageObject, reader: PdfReader) -> PageObject:
    """Move the lower resume body without duplicating hidden PDF text."""
    result = copy.deepcopy(page)
    content = ContentStream(result.get_contents(), reader)

    for operands, operator in content.operations:
        if operator == b"Tm":
            y = float(operands[5])
            if MOVABLE_TOP <= y < MOVABLE_BOTTOM:
                operands[5] = FloatObject(y + SHIFT)
        elif operator == b"re":
            y = float(operands[1])
            if MOVABLE_TOP <= y < MOVABLE_BOTTOM:
                operands[1] = FloatObject(y + SHIFT)
        elif operator in {b"m", b"l"}:
            y = float(operands[1])
            if MOVABLE_TOP <= y < MOVABLE_BOTTOM:
                operands[1] = FloatObject(y + SHIFT)
        elif operator == b"c":
            ys = [float(operands[index]) for index in (1, 3, 5)]
            if all(MOVABLE_TOP <= y < MOVABLE_BOTTOM for y in ys):
                for index, y in zip((1, 3, 5), ys):
                    operands[index] = FloatObject(y + SHIFT)
        elif operator in {b"v", b"y"}:
            ys = [float(operands[index]) for index in (1, 3)]
            if all(MOVABLE_TOP <= y < MOVABLE_BOTTOM for y in ys):
                for index, y in zip((1, 3), ys):
                    operands[index] = FloatObject(y + SHIFT)

    result.replace_contents(content)
    if NameObject("/Annots") in result:
        del result[NameObject("/Annots")]
    return result


def make_overlay(width: float, height: float) -> PageObject:
    pdfmetrics.registerFont(TTFont("STHeitiSC-Light", REGULAR_FONT, subfontIndex=1))
    pdfmetrics.registerFont(TTFont("STHeitiSC-Medium", BOLD_FONT, subfontIndex=1))

    stream = BytesIO()
    c = canvas.Canvas(stream, pagesize=(width, height), pageCompression=1)

    company = "某传统互联网公司"
    role = "前端开发"
    date = "2026.03-至今"
    description = "负责娱乐站点页面及后台的迭代与开发。"

    company_x = 43.92
    company_size = 9.5
    header_baseline = height - 365.136

    c.setFillColorRGB(0.137, 0.137, 0.137)
    c.setFont("STHeitiSC-Medium", company_size)
    c.drawString(company_x, header_baseline, company)

    company_width = pdfmetrics.stringWidth(company, "STHeitiSC-Medium", company_size)
    separator_x = company_x + company_width + 6.10

    c.setFillColorRGB(0.373, 0.373, 0.373)
    c.setFont("STHeitiSC-Light", 9.0)
    c.drawString(separator_x, header_baseline, "|")
    c.drawString(separator_x + 9.36, header_baseline, role)

    c.setFont("STHeitiSC-Light", 8.5)
    date_width = pdfmetrics.stringWidth(date, "STHeitiSC-Light", 8.5)
    c.drawString(548.55 - date_width, height - 364.494, date)
    c.drawString(48.24, height - 381.773, description)

    c.save()
    stream.seek(0)
    return PdfReader(stream).pages[0]


def build() -> None:
    reader = PdfReader(SOURCE)
    original = reader.pages[0]
    width = float(original.mediabox.width)
    height = float(original.mediabox.height)

    rebuilt = move_page_content(original, reader)
    rebuilt.merge_page(make_overlay(width, height))

    writer = PdfWriter()
    writer.add_page(rebuilt)
    for page in reader.pages[1:]:
        writer.add_page(page)

    if reader.metadata:
        metadata = {
            str(key): str(value)
            for key, value in reader.metadata.items()
            if key and value is not None
        }
        writer.add_metadata(metadata)

    original_link = reader.pages[0]["/Annots"][0].get_object()
    original_rect = [float(value) for value in original_link["/Rect"]]
    moved_rect = RectangleObject(
        (
            original_rect[0],
            original_rect[1] - SHIFT,
            original_rect[2],
            original_rect[3] - SHIFT,
        )
    )
    uri = str(original_link["/A"].get_object()["/URI"])
    writer.add_uri(0, uri, moved_rect, border=[0, 0, 0])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("wb") as target:
        writer.write(target)


if __name__ == "__main__":
    build()
