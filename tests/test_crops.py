from sqlalchemy import text

from tests.conftest import engine


async def seed():
    async with engine.begin() as conn:
        await conn.execute(text("INSERT INTO crop_seasons (id, name) VALUES (1, 'Rabi'), (2, 'Kharif')"))
        await conn.execute(text(
            "INSERT INTO crop_types (season_id, name) VALUES (1, 'Wheat'), (2, 'Cotton'), (2, 'Rice')"
        ))


async def test_list_seasons(client):
    await seed()
    r = await client.get("/api/crops/seasons/")
    assert [s["name"] for s in r.json()] == ["Kharif", "Rabi"]  # ordered by name


async def test_crops_filtered_by_season(client):
    await seed()
    r = await client.get("/api/crops/types/", params={"season_id": 2})
    assert [c["name"] for c in r.json()] == ["Cotton", "Rice"]
