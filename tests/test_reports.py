from datetime import date

from app.modules.reports import service
from app.modules.reports.pdf import build_pdf
from tests.test_farms import SQUARE, login_as
from app.main import app

from app.core.urdu import urdu_paragraph, wrap_logical

from app.integrations import sentinel

import io

from PIL import Image
from shapely.geometry import Polygon
from sqlalchemy import text

from app.modules.reports.pdf import outlined_image
from tests.conftest import engine

RING = [[74.35, 31.52], [74.351, 31.52], [74.351, 31.521], [74.35, 31.521], [74.35, 31.52]]

LONG = "پہلا " + "لفظ " * 80 + "آخری"

SAMPLE = {
    "farm": {"name": "Test field", "crop": "Cotton", "area_acres": 2.47, "sowing_date": date(2026, 8, 28)},
    "days_since_sowing": 76,
    "stage": {"name": "Square Formation", "day_from": 61, "day_to": 90},
    "satellite_date": "2026-11-10",
    "clear_pct": 100,
    "indices": [
        {"index": "NDVI", "value": 0.589, "low": 0.4, "high": 0.5, "status": "high", "dominant_color": "YELLOW"},
        {"index": "NDMI", "value": 0.12, "low": None, "high": None, "status": "no_reference", "dominant_color": None},
    ],
}


def test_build_pdf_makes_a_pdf():
    pdf = build_pdf(SAMPLE)
    assert pdf.startswith(b"%PDF")       # every PDF file starts like this
    assert pdf.rstrip().endswith(b"%%EOF")  # ...and ends like this
    assert len(pdf) > 1000


def test_build_pdf_without_stage():
    assert build_pdf({**SAMPLE, "stage": None}).startswith(b"%PDF")


# async def test_report_endpoint(client, monkeypatch):
#     async def fake_health(db, user, farm_id):
#         return {k: v for k, v in SAMPLE.items() if k != "farm"}

#     monkeypatch.setattr(service, "farm_health", fake_health)
#     h = await login_as(client, "03001111111")
#     farm_id = (await client.post("/api/farms/", headers=h, json={"name": "F", "boundary": SQUARE})).json()["id"]

#     r = await client.get(f"/api/farms/{farm_id}/report/", headers=h)
#     assert r.status_code == 200
#     assert r.headers["content-type"] == "application/pdf"
#     assert r.content.startswith(b"%PDF")


# async def test_other_users_report_404(client, monkeypatch):
#     async def fake_health(db, user, farm_id):
#         raise AssertionError("must not be called for someone else's farm")

#     monkeypatch.setattr(service, "farm_health", fake_health)
#     owner = await login_as(client, "03001111111")
#     farm_id = (await client.post("/api/farms/", headers=owner, json={"name": "F", "boundary": SQUARE})).json()["id"]
#     other = await login_as(client, "03002222222")
#     assert (await client.get(f"/api/farms/{farm_id}/report/", headers=other)).status_code == 404

def test_report_route_is_registered():
    paths = app.openapi()["paths"]
    assert "/api/farms/{farm_id}/report/" in paths



def test_urdu_wraps_in_reading_order():
    lines = wrap_logical(LONG, width=300)
    assert len(lines) > 1
    assert lines[0].startswith("پہلا")   # first word stays on the FIRST line
    assert lines[-1].endswith("آخری")    # last word on the LAST line


def test_urdu_paragraph_survives_markup_characters():
    urdu_paragraph("فصل & <کھاد>", width=300)  # must not raise


def test_pdf_with_urdu_sections():
    report = {**SAMPLE, "indices": [{
        **SAMPLE["indices"][0],
        "title": "نشوونما",
        "paragraph": "NDVI کے تجزیے کے مطابق، فصل کے زیرِ جائزہ رقبے میں 62.5 فیصد زرد رنگ غالب ہے۔",
        "guidance": {"special_instructions": "معائنہ کریں", "practical_actions": "آبپاشی کریں"},
    }]}
    assert build_pdf(report).startswith(b"%PDF")



async def test_report_endpoint(client, monkeypatch):
    async def fake_health(db, farm):
        return {k: v for k, v in SAMPLE.items() if k != "farm"}

    async def fake_images(poly):
        return {"NDVI": png_bytes(), "NDMI": None}

    monkeypatch.setattr(service, "farm_health_for", fake_health)
    monkeypatch.setattr(sentinel, "fetch_all_index_pngs", fake_images)
    h = await login_as(client, "03001111111")
    farm_id = (await client.post("/api/farms/", headers=h, json={
        "name": "F", "boundary": SQUARE, "crop_id": None,
    })).json()["id"]

    # check_ready needs a crop + sowing date, so give the farm one directly
    async with engine.begin() as conn:
        await conn.execute(text("INSERT INTO crop_seasons (id, name) VALUES (1, 'Kharif')"))
        await conn.execute(text("INSERT INTO crop_types (id, season_id, name) VALUES (1, 1, 'Cotton')"))
        await conn.execute(text(f"UPDATE farms SET crop_id = 1, sowing_date = '2026-08-28' WHERE id = {farm_id}"))

    r = await client.get(f"/api/farms/{farm_id}/report/", headers=h)
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")


async def test_other_users_report_404(client, monkeypatch):
    async def must_not_run(*args):
        raise AssertionError("must not be called for someone else's farm")

    monkeypatch.setattr(service, "farm_health_for", must_not_run)
    monkeypatch.setattr(sentinel, "fetch_all_index_pngs", must_not_run)
    owner = await login_as(client, "03001111111")
    farm_id = (await client.post("/api/farms/", headers=owner, json={"name": "F", "boundary": SQUARE})).json()["id"]
    other = await login_as(client, "03002222222")
    assert (await client.get(f"/api/farms/{farm_id}/report/", headers=other)).status_code == 404







def png_bytes(w: int = 120, h: int = 100) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (w, h), (120, 200, 90, 255)).save(buf, "PNG")
    return buf.getvalue()


def test_outlined_image_keeps_shape():
    img = outlined_image(png_bytes(200, 100), RING)
    assert round(img.drawWidth / img.drawHeight, 2) == 2.0  # 200×100 stays 2:1


def test_pdf_with_images_is_bigger():
    with_images = build_pdf({**SAMPLE, "farm": {**SAMPLE["farm"], "ring": RING},
                             "images": {"NDVI": png_bytes()}})
    assert len(with_images) > len(build_pdf(SAMPLE))


async def test_one_failed_image_does_not_break_the_rest(monkeypatch):
    async def fake_png(poly, index):
        if index == "NDMI":
            raise RuntimeError("boom")
        return b"png"

    monkeypatch.setattr(sentinel, "fetch_index_png", fake_png)
    poly = Polygon(RING)
    images = await sentinel.fetch_all_index_pngs(poly)
    assert images["NDMI"] is None
    assert images["NDVI"] == b"png"
    assert len(images) == 6
