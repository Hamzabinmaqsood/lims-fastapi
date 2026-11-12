from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.report_content.models import ColorZone, GuidanceTemplate, ParagraphTemplate


Zones = dict[str, list[tuple[str, float]]]  # {"NDVI": [("RED", -1.0), ("YELLOW", 0.4), ...]}


async def load_zones(db: AsyncSession) -> Zones:
    rows = (await db.scalars(
        select(ColorZone).order_by(ColorZone.index_name, ColorZone.min_value)
    )).all()
    zones: Zones = {}
    for z in rows:
        zones.setdefault(z.index_name, []).append((z.color, float(z.min_value)))
    return zones


async def load_texts(db: AsyncSession) -> tuple[dict, dict]:
    paragraphs = {(p.index_name, p.color): p.body for p in await db.scalars(select(ParagraphTemplate))}
    guidance = {g.index_name: g for g in await db.scalars(select(GuidanceTemplate))}
    return paragraphs, guidance
