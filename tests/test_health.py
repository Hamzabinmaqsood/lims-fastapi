from datetime import date, timedelta
from types import SimpleNamespace

from sqlalchemy import text

from app.integrations import sentinel
from app.modules.satellite.health import assess, add_zones
from tests.conftest import engine
from tests.test_farms import SQUARE, login_as


def rng(index, low, high):
    return SimpleNamespace(index_name=index, low=low, high=high, title="t", description="d")


def test_assess_statuses():
    result = assess(
        {"NDVI": 0.30, "SAVI": 0.50, "NDMI": 0.90, "RECI": 1.2},
        [rng("NDVI", 0.4, 0.5), rng("SAVI", 0.4, 0.6), rng("NDMI", 0.2, 0.4)],
    )
    status = {r["index"]: r["status"] for r in result}
    assert status == {"NDVI": "low", "SAVI": "normal", "NDMI": "high", "RECI": "no_reference"}


def test_assess_edges_are_normal():
    result = assess({"NDVI": 0.4}, [rng("NDVI", 0.4, 0.5)])  # exactly on the boundary
    assert result[0]["status"] == "normal"


async def seed_stage():
    async with engine.begin() as conn:
        await conn.execute(text("INSERT INTO crop_seasons (id, name) VALUES (1, 'Kharif')"))
        await conn.execute(text("INSERT INTO crop_types (id, season_id, name) VALUES (1, 1, 'Cotton')"))
        await conn.execute(text(
            "INSERT INTO growth_stages (id, crop_id, name, day_from, day_to) VALUES (1, 1, 'Vegetative', 31, 60)"
        ))
        await conn.execute(text(
            "INSERT INTO growth_stage_index_ranges (stage_id, index_name, low, high, title) "
            "VALUES (1, 'NDVI', 0.25, 0.35, 'Growth')"
        ))


async def test_health_endpoint(client, monkeypatch):
    await seed_stage()

    async def fake_stats(poly, zones, days=30):
        return {"date": "2026-11-10", "clear_pct": 100, "indices": {"NDVI": 0.20, "NDMI": 0.1}, "zones": {"NDVI": {"RED": 70.0, "YELLOW": 20.0, "LIGHT_GREEN": 10.0, "GREEN": 0.0}}}

    monkeypatch.setattr(sentinel, "fetch_index_stats", fake_stats)
    h = await login_as(client, "03001111111")
    sown = (date.today() - timedelta(days=40)).isoformat()
    farm = (await client.post("/api/farms/", headers=h, json={
        "name": "Cotton field", "boundary": SQUARE, "crop_id": 1, "sowing_date": sown,
    })).json()

    r = await client.get(f"/api/farms/{farm['id']}/health/", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["days_since_sowing"] == 40
    assert body["stage"]["name"] == "Vegetative"
    status = {i["index"]: i["status"] for i in body["indices"]}
    assert status == {"NDVI": "low", "NDMI": "no_reference"}
    ndvi = next(i for i in body["indices"] if i["index"] == "NDVI")
    assert ndvi["dominant_color"] == "RED"


async def test_health_needs_crop_and_sowing_date(client, monkeypatch):
    called = False

    async def fake_stats(poly, zones, days=30):
        nonlocal called
        called = True

    monkeypatch.setattr(sentinel, "fetch_index_stats", fake_stats)
    h = await login_as(client, "03001111111")
    farm = (await client.post("/api/farms/", headers=h, json={"name": "F", "boundary": SQUARE})).json()
    r = await client.get(f"/api/farms/{farm['id']}/health/", headers=h)
    assert r.status_code == 400
    assert called is False  # fail fast: no satellite call was made



def test_add_zones_picks_dominant():
    result = add_zones([{"index": "NDVI"}, {"index": "SAVI"}],
                       {"NDVI": {"RED": 10.0, "GREEN": 70.0}})
    assert result[0]["dominant_color"] == "GREEN"
    assert result[1]["dominant_color"] is None  # no zones configured
