"""Urdu for ReportLab: Amiri font + letter joining + right-to-left lines."""

from pathlib import Path
from xml.sax.saxutils import escape

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"  # app/assets/fonts

pdfmetrics.registerFont(TTFont("Urdu", str(FONTS / "Amiri-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Urdu-Bold", str(FONTS / "Amiri-Bold.ttf")))

_RESHAPER = arabic_reshaper.ArabicReshaper({"language": "Urdu", "support_ligatures": True})

STYLE = ParagraphStyle("urdu", fontName="Urdu", fontSize=12, leading=22, alignment=TA_RIGHT, spaceAfter=6)
BOLD = ParagraphStyle("urdu-bold", parent=STYLE, fontName="Urdu-Bold", fontSize=13)


def wrap_logical(text: str, width: float, font: str = "Urdu", size: float = 12) -> list[str]:
    """Split into lines that fit `width`, still in normal reading order."""
    lines, current = [], []
    for word in text.split():
        trial = " ".join(current + [word])
        if current and pdfmetrics.stringWidth(_RESHAPER.reshape(trial), font, size) > width * 0.97:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def urdu_paragraph(text: str, width: float, bold: bool = False) -> Paragraph:
    """Wrap FIRST, then join letters and reverse each line on its own."""
    style = BOLD if bold else STYLE
    lines = wrap_logical(text, width, style.fontName, style.fontSize)
    display = [escape(get_display(_RESHAPER.reshape(line))) for line in lines]
    return Paragraph("<br/>".join(display), style)
