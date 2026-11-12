from types import SimpleNamespace

from app.modules.report_content.render import attach_texts, render


def test_render_fills_known_placeholders():
    assert render("{index_name}: {red_percentage}", {"index_name": "NDVI", "red_percentage": "5.0 فیصد"}) \
        == "NDVI: 5.0 فیصد"


def test_render_leaves_unknown_and_unsafe_placeholders():
    assert render("{unknown} {user.__class__}", {}) == "{unknown} {user.__class__}"


def test_paragraph_follows_dominant_colour():
    paragraphs = {("NDVI", "RED"): "سرخ {red_percentage}", ("NDVI", "GREEN"): "سبز {green_percentage}"}
    item = {"index": "NDVI", "dominant_color": "RED", "zones": {"RED": 62.5, "GREEN": 37.5}}
    result = attach_texts([item], paragraphs, {})[0]
    assert result["paragraph"] == "سرخ 62.5 فیصد"


def test_guidance_only_when_red_over_half():
    g = {"NDVI": SimpleNamespace(special_instructions="s", practical_actions="a")}
    red = attach_texts([{"index": "NDVI", "dominant_color": "RED", "zones": {"RED": 70}}], {}, g)[0]
    ok = attach_texts([{"index": "NDVI", "dominant_color": "GREEN", "zones": {"RED": 10}}], {}, g)[0]
    assert red["guidance"]["practical_actions"] == "a"
    assert ok["guidance"] is None


def test_no_zones_gives_unavailable_text():
    result = attach_texts([{"index": "NDMI", "dominant_color": None, "zones": None}], {}, {})[0]
    assert "NDMI" in result["paragraph"]
