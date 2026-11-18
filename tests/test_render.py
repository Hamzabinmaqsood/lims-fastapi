from types import SimpleNamespace

from app.modules.report_content.render import attach_texts, render


from PIL import Image
from app.modules.reports.farm_mask import class_maps, farm_mask


from io import BytesIO

from PIL import Image

from app.integrations import sentinel
from app.modules.reports.farm_mask import class_maps, class_percents, farm_mask
from app.modules.reports.pdf import build_pdf  # noqa: F401  (import check)

ZONES = [("RED", -1), ("YELLOW", 0.4), ("LIGHT_GREEN", 0.65), ("GREEN", 0.8)]



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



def test_only_present_classes_get_a_map():
    img = Image.new("RGB", (10, 10), (0, 200, 0))
    classes = Image.new("L", (10, 10), 1)                    # every pixel "good"
    mask = farm_mask((10, 10), [(0, 0), (9, 0), (9, 9), (0, 9)])
    assert list(class_maps(img, mask, classes)) == ["good"]  # no normal/bad images



def test_class_script_uses_same_limits_as_stats():
    js = sentinel.class_evalscript("NDVI", ZONES)
    assert "if (v >= 0.8) return [1];" in js       # GREEN → good
    assert "if (v >= 0.65) return [1];" in js      # LIGHT_GREEN → good
    assert "if (v >= 0.4) return [2];" in js       # YELLOW → normal
    assert "return [3];" in js                     # below 0.4 → bad
    assert js.index("0.8") < js.index("0.65") < js.index("0.4")   # highest checked first


def test_percents_count_only_inside_farm():
    classes = Image.new("L", (10, 10), 1)
    classes.paste(3, (0, 0, 5, 10))                # left half bad, right half good
    whole = farm_mask((10, 10), [(0, 0), (9, 0), (9, 9), (0, 9)])
    right = farm_mask((10, 10), [(5, 0), (9, 0), (9, 9), (5, 9)])
    assert class_percents(whole, classes) == {"good": 50.0, "normal": 0.0, "bad": 50.0}
    assert class_percents(right, classes)["bad"] == 0.0           # bad pixels are outside this farm
    assert list(class_maps(Image.new("RGB", (10, 10)), right, classes)) == ["good"]
