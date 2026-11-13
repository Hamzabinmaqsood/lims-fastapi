"""Save each satellite reading and compare it with earlier weeks."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.satellite.models import IndexSnapshot


async def save_snapshots(db: AsyncSession, farm_id: int, observed_on: date, indices: list[dict]) -> None:
    """Upsert one row per index. Calling this twice for the same date changes nothing extra."""
    rows = []
    for i in indices:
        zones = i.get("zones") or {}
        rows.append({
            "farm_id": farm_id,
            "observed_on": observed_on,
            "index_name": i["index"],
            "value": i["value"],
            "dominant_color": i.get("dominant_color"),
            "red_pct": zones.get("RED"),
            "yellow_pct": zones.get("YELLOW"),
            "light_green_pct": zones.get("LIGHT_GREEN"),
            "green_pct": zones.get("GREEN"),
        })
    if not rows:
        return
    stmt = insert(IndexSnapshot).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["farm_id", "observed_on", "index_name"],
        set_={col: stmt.excluded[col] for col in
              ("value", "dominant_color", "red_pct", "yellow_pct", "light_green_pct", "green_pct")},
    )
    await db.execute(stmt)
    await db.commit()


async def load_history(db: AsyncSession, farm_id: int, before: date, days: int = 60) -> dict[str, list[dict]]:
    """Earlier readings (newest first) per index, from the last `days` days."""
    q = (
        select(IndexSnapshot.index_name, IndexSnapshot.observed_on, IndexSnapshot.value)
        .where(
            IndexSnapshot.farm_id == farm_id,
            IndexSnapshot.observed_on < before,
            IndexSnapshot.observed_on >= before - timedelta(days=days),
        )
        .order_by(IndexSnapshot.observed_on.desc())
    )
    history: dict[str, list[dict]] = {}
    for name, observed_on, value in (await db.execute(q)).all():
        history.setdefault(name, []).append({"date": observed_on, "value": float(value)})
    return history


def add_changes(indices: list[dict], history: dict[str, list[dict]], current: date) -> list[dict]:
    """Attach last week's value and the change, for each index.
    'Last week' = the newest earlier reading 5–21 days before this one (Django's window)."""
    for i in indices:
        previous = next(
            (h for h in history.get(i["index"], []) if 5 <= (current - h["date"]).days <= 21),
            None,
        )
        i["previous"] = previous
        i["change"] = round(i["value"] - previous["value"], 3) if previous else None
    return indices
