from sqlalchemy import text, update

from app.modules.users.models import User
from tests.conftest import TestSession, engine
from tests.test_farms import login_as

STAGE = {
    "crop_id": 1, "name": "Tillering", "day_from": 21, "day_to": 45,
    "ranges": [{"index_name": "NDVI", "low": 0.35, "high": 0.72, "title": "Good growth"}],
}


async def setup(client) -> tuple[dict, dict]:
    async with engine.begin() as conn:
        await conn.execute(text("INSERT INTO crop_seasons (id, name) VALUES (1, 'Rabi')"))
        await conn.execute(text("INSERT INTO crop_types (id, season_id, name) VALUES (1, 1, 'Wheat')"))
    farmer = await login_as(client, "03001111111")
    admin = await login_as(client, "03002222222")
    async with TestSession() as db:
        await db.execute(update(User).where(User.mobile_number == "03002222222").values(is_superuser=True))
        await db.commit()
    return farmer, admin


async def test_admin_creates_and_farmer_lists(client):
    farmer, admin = await setup(client)
    r = await client.post("/api/growth-stages/", headers=admin, json=STAGE)
    assert r.status_code == 201
    assert r.json()["ranges"][0]["index_name"] == "NDVI"

    r = await client.get("/api/growth-stages/", headers=farmer, params={"crop_id": 1})
    assert [s["name"] for s in r.json()] == ["Tillering"]


async def test_farmer_cannot_create_403(client):
    farmer, _ = await setup(client)
    assert (await client.post("/api/growth-stages/", headers=farmer, json=STAGE)).status_code == 403


async def test_overlapping_days_400(client):
    _, admin = await setup(client)
    await client.post("/api/growth-stages/", headers=admin, json=STAGE)
    r = await client.post("/api/growth-stages/", headers=admin,
                          json={**STAGE, "name": "Jointing", "day_from": 40, "day_to": 60})
    assert r.status_code == 400


async def test_low_above_high_422(client):
    _, admin = await setup(client)
    bad = {**STAGE, "ranges": [{"index_name": "NDVI", "low": 0.9, "high": 0.2}]}
    assert (await client.post("/api/growth-stages/", headers=admin, json=bad)).status_code == 422


async def test_put_replaces_ranges(client):
    _, admin = await setup(client)
    stage_id = (await client.post("/api/growth-stages/", headers=admin, json=STAGE)).json()["id"]
    new = {**STAGE, "ranges": [{"index_name": "NDMI", "low": 0.1, "high": 0.4}]}
    r = await client.put(f"/api/growth-stages/{stage_id}/", headers=admin, json=new)
    assert [x["index_name"] for x in r.json()["ranges"]] == ["NDMI"]
