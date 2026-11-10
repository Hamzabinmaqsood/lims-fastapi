from sqlalchemy import text

from tests.conftest import engine
from tests.test_auth import USER

# ~100 m × 100 m square in Lahore ≈ 10,000 m² ≈ 2.47 acres
SQUARE = [[31.5200, 74.3500], [31.5209, 74.3500], [31.5209, 74.35106], [31.5200, 74.35106]]


async def login_as(client, mobile: str) -> dict:
    await client.post("/api/user/signup/", json={**USER, "mobile_number": mobile})
    r = await client.post("/api/token/", json={"mobile_number": mobile, "password": USER["password"]})
    return {"Authorization": f"Bearer {r.json()['access']}"}


async def test_create_farm_calculates_acres(client):
    h = await login_as(client, "03001111111")
    r = await client.post("/api/farms/", headers=h, json={"name": "Home", "boundary": SQUARE})
    assert r.status_code == 201
    assert 2.3 < r.json()["area_acres"] < 2.6


async def test_farms_are_private(client):
    owner = await login_as(client, "03001111111")
    other = await login_as(client, "03002222222")
    farm_id = (await client.post("/api/farms/", headers=owner, json={"name": "Test", "boundary": SQUARE})).json()["id"]

    assert (await client.get("/api/farms/", headers=other)).json() == []
    assert (await client.get(f"/api/farms/{farm_id}/", headers=other)).status_code == 404
    assert (await client.delete(f"/api/farms/{farm_id}/", headers=other)).status_code == 404


async def test_two_points_is_422(client):
    h = await login_as(client, "03001111111")
    r = await client.post("/api/farms/", headers=h, json={"name": "Test", "boundary": SQUARE[:2]})
    assert r.status_code == 422


async def test_crossing_lines_is_400(client):
    h = await login_as(client, "03001111111")
    bowtie = [SQUARE[0], SQUARE[2], SQUARE[1], SQUARE[3]]  # an X shape
    r = await client.post("/api/farms/", headers=h, json={"name": "Test", "boundary": bowtie})
    assert r.status_code == 400


async def test_update_boundary_recalculates_acres(client):
    h = await login_as(client, "03001111111")
    farm_id = (await client.post("/api/farms/", headers=h, json={"name": "Test", "boundary": SQUARE})).json()["id"]
    half = [SQUARE[0], [31.52045, 74.3500], [31.52045, 74.35106], SQUARE[3]]
    r = await client.patch(f"/api/farms/{farm_id}/", headers=h, json={"name": "Test", "boundary": half})
    assert 1.1 < r.json()["area_acres"] < 1.3


async def test_wrong_crop_for_season_is_400(client):
    async with engine.begin() as conn:
        await conn.execute(text("INSERT INTO crop_seasons (id, name) VALUES (1, 'Rabi'), (2, 'Kharif')"))
        await conn.execute(text("INSERT INTO crop_types (id, season_id, name) VALUES (1, 1, 'Wheat')"))
    h = await login_as(client, "03001111111")
    r = await client.post("/api/farms/", headers=h,
                          json={"name": "Test", "boundary": SQUARE, "crop_season_id": 2, "crop_id": 1})
    assert r.status_code == 400


async def test_delete_farm(client):
    h = await login_as(client, "03001111111")
    farm_id = (await client.post("/api/farms/", headers=h, json={"name": "Test", "boundary": SQUARE})).json()["id"]
    assert (await client.delete(f"/api/farms/{farm_id}/", headers=h)).status_code == 204
    assert (await client.get(f"/api/farms/{farm_id}/", headers=h)).status_code == 404

async def test_blank_name_is_422(client):
    h = await login_as(client, "03001111111")
    for name in ["", "   "]:
        r = await client.post("/api/farms/", headers=h, json={"name": name, "boundary": SQUARE})
        assert r.status_code == 422


async def test_missing_name_is_422(client):
    h = await login_as(client, "03001111111")
    r = await client.post("/api/farms/", headers=h, json={"boundary": SQUARE})
    assert r.status_code == 422
