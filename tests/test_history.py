from datetime import date

from sqlalchemy import func, select

from app.modules.satellite.history import add_changes, load_history, save_snapshots
from app.modules.satellite.models import IndexSnapshot
from tests.conftest import TestSession
from tests.test_farms import SQUARE, login_as


async def make_farm(client) -> int:
    h = await login_as(client, "03001111111")
    return (await client.post("/api/farms/", headers=h, json={"name": "F", "boundary": SQUARE})).json()["id"]


def test_change_uses_reading_5_to_21_days_old():
    history = {"NDVI": [
        {"date": date(2026, 11, 8), "value": 0.70},   # 2 days old → too recent, skipped
        {"date": date(2026, 11, 1), "value": 0.62},   # 9 days old → "last week"
    ]}
    result = add_changes([{"index": "NDVI", "value": 0.48}], history, date(2026, 11, 10))[0]
    assert result["previous"]["value"] == 0.62
    assert result["change"] == -0.14


def test_no_history_means_no_change():
    result = add_changes([{"index": "NDVI", "value": 0.5}], {}, date(2026, 11, 10))[0]
    assert result["previous"] is None and result["change"] is None


async def test_save_is_idempotent(client):
    farm_id = await make_farm(client)
    indices = [{"index": "NDVI", "value": 0.5, "zones": {"RED": 10.0}, "dominant_color": "RED"}]
    async with TestSession() as db:
        await save_snapshots(db, farm_id, date(2026, 11, 10), indices)
        await save_snapshots(db, farm_id, date(2026, 11, 10), [{**indices[0], "value": 0.6}])
        count = await db.scalar(select(func.count()).select_from(IndexSnapshot))
        value = await db.scalar(select(IndexSnapshot.value))
    assert count == 1            # same farm + date + index → still ONE row
    assert float(value) == 0.6   # ...updated with the newer value


async def test_history_excludes_current_date(client):
    farm_id = await make_farm(client)
    async with TestSession() as db:
        await save_snapshots(db, farm_id, date(2026, 11, 1), [{"index": "NDVI", "value": 0.62}])
        await save_snapshots(db, farm_id, date(2026, 11, 10), [{"index": "NDVI", "value": 0.48}])
        history = await load_history(db, farm_id, before=date(2026, 11, 10))
    assert [h["date"] for h in history["NDVI"]] == [date(2026, 11, 1)]
