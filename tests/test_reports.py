from datetime import date

from app.modules.reports import service
from app.modules.reports.pdf import build_pdf
from tests.test_farms import SQUARE, login_as
from app.main import app

from app.core.urdu import urdu_paragraph, wrap_logical

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


async def test_report_endpoint(client, monkeypatch):
    async def fake_health(db, user, farm_id):
        return {k: v for k, v in SAMPLE.items() if k != "farm"}

    monkeypatch.setattr(service, "farm_health", fake_health)
    h = await login_as(client, "03001111111")
    farm_id = (await client.post("/api/farms/", headers=h, json={"name": "F", "boundary": SQUARE})).json()["id"]

    r = await client.get(f"/api/farms/{farm_id}/report/", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


async def test_other_users_report_404(client, monkeypatch):
    async def fake_health(db, user, farm_id):
        raise AssertionError("must not be called for someone else's farm")

    monkeypatch.setattr(service, "farm_health", fake_health)
    owner = await login_as(client, "03001111111")
    farm_id = (await client.post("/api/farms/", headers=owner, json={"name": "F", "boundary": SQUARE})).json()["id"]
    other = await login_as(client, "03002222222")
    assert (await client.get(f"/api/farms/{farm_id}/report/", headers=other)).status_code == 404

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
