"""Build the farm report PDF from report data (no DB, no network)."""

from io import BytesIO

from PIL import Image as PILImage
from PIL import ImageDraw
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.urdu import urdu_paragraph

STATUS_COLORS = {
    "low": colors.HexColor("#d7191c"),
    "normal": colors.HexColor("#1a9641"),
    "high": colors.HexColor("#e08a00"),
    "no_reference": colors.grey,
}
GRID = [
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bbbbbb")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]


def _farm_table(report: dict) -> Table:
    farm, stage = report["farm"], report["stage"]
    rows = [
        ["Farm", farm["name"]],
        ["Crop", farm["crop"] or "—"],
        ["Area", f"{farm['area_acres']:.2f} acres"],
        ["Sowing date", str(farm["sowing_date"])],
        ["Crop age", f"{report['days_since_sowing']} days"],
        ["Growth stage", f"{stage['name']} (days {stage['day_from']}–{stage['day_to']})" if stage else "Unknown"],
        ["Satellite image", f"{report['satellite_date']} ({report['clear_pct']}% cloud-free)"],
    ]
    table = Table(rows, colWidths=[4.5 * cm, 12 * cm])
    table.setStyle(TableStyle(GRID + [
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f2f2")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ]))
    return table


def _index_table(report: dict) -> Table:
    rows = [["Index", "Value", "Healthy range", "Status", "Dominant colour"]]
    for i in report["indices"]:
        rows.append([
            i["index"],
            f"{i['value']:.3f}",
            f"{i['low']} – {i['high']}" if i["low"] is not None else "—",
            i["status"].replace("_", " ").upper(),
            (i["dominant_color"] or "—").replace("_", " "),
        ])
    style = GRID + [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a6b3c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]
    for row, i in enumerate(report["indices"], start=1):  # colour each Status cell
        style += [
            ("TEXTCOLOR", (3, row), (3, row), STATUS_COLORS[i["status"]]),
            ("FONTNAME", (3, row), (3, row), "Helvetica-Bold"),
        ]
    table = Table(rows, colWidths=[2.5 * cm, 2.5 * cm, 4 * cm, 3.5 * cm, 4 * cm])
    table.setStyle(TableStyle(style))
    return table


def build_pdf(report: dict) -> bytes:
    buffer = BytesIO()  # build the PDF in memory, not on disk
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"Crop Health Report – {report['farm']['name']}",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Crop Health Report", styles["Title"]),
        _farm_table(report),
        Spacer(1, 0.7 * cm),
        Paragraph("Satellite index summary", styles["Heading2"]),
        _index_table(report),
        *_index_sections(report, doc.width),
    ]
    doc.build(story)
    return buffer.getvalue()


def _index_sections(report: dict, width: float) -> list:
    styles = getSampleStyleSheet()
    story = [Spacer(1, 0.7 * cm), Paragraph("Detailed analysis", styles["Heading2"])]
    for i in report["indices"]:
        block = [Paragraph(f"{i['index']} — {i['status'].replace('_', ' ').upper()}", styles["Heading3"])]
        png = (report.get("images") or {}).get(i["index"])
        if png:
            block.append(outlined_image(png, report["farm"]["ring"]))
            block.append(Spacer(1, 0.2 * cm))
        if i.get("title"):
            block.append(urdu_paragraph(i["title"], width, bold=True))
        if i.get("description"):
            block.append(urdu_paragraph(i["description"], width))
        if i.get("paragraph"):
            block.append(urdu_paragraph(i["paragraph"], width))
        if i.get("guidance"):
            block += [
                urdu_paragraph("خصوصی ہدایات", width, bold=True),  # "Special instructions"
                urdu_paragraph(i["guidance"]["special_instructions"], width),
                urdu_paragraph("عملی اقدامات", width, bold=True),  # "Practical actions"
                urdu_paragraph(i["guidance"]["practical_actions"], width),
            ]
        story.append(KeepTogether(block))  # don't split one index across two pages
    return story



def outlined_image(png: bytes, ring: list[list[float]], max_w: float = 8 * cm, max_h: float = 8 * cm) -> RLImage:
    """Satellite PNG with the farm boundary drawn on top, sized to fit max_w × max_h."""
    img = PILImage.open(BytesIO(png)).convert("RGBA")
    w, h = img.size

    # The image covers exactly the farm's bounding box, so lng/lat map straight to pixels.
    lngs, lats = [p[0] for p in ring], [p[1] for p in ring]
    min_lng, max_lng, min_lat, max_lat = min(lngs), max(lngs), min(lats), max(lats)

    def to_px(lng: float, lat: float) -> tuple[float, float]:
        x = (lng - min_lng) / ((max_lng - min_lng) or 1) * (w - 1)
        y = (max_lat - lat) / ((max_lat - min_lat) or 1) * (h - 1)  # pixel y grows DOWNWARD
        return x, y

    ImageDraw.Draw(img).line([to_px(lng, lat) for lng, lat in ring], fill=(0, 0, 0, 255), width=3)

    out = BytesIO()
    img.save(out, "PNG")
    out.seek(0)
    scale = min(max_w / w, max_h / h)
    return RLImage(out, width=w * scale, height=h * scale)
