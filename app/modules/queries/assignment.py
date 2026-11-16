"""Pick the Response_Team member for a new query: sticky first, then least busy."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.queries.models import Query
from app.modules.users.models import ROLE_RESPONSE_TEAM, Role, User


def _active_team():
    """SELECT for active Response_Team users (reused by both rules)."""
    return (
        select(User.id)
        .join(Role, User.role_id == Role.id)
        .where(Role.name == ROLE_RESPONSE_TEAM, User.is_active.is_(True))
    )


async def sticky_member(db: AsyncSession, farmer_id: int) -> int | None:
    """The member who handled this farmer's latest query — if still an active team member."""
    previous = await db.scalar(
        select(Query.assigned_to_id)
        .where(Query.user_id == farmer_id, Query.assigned_to_id.is_not(None))
        .order_by(Query.assigned_at.desc())
        .limit(1)
    )
    if previous is None:
        return None
    return await db.scalar(_active_team().where(User.id == previous))


async def least_busy_member(db: AsyncSession) -> int | None:
    """The active team member with the fewest PENDING queries (ties → lowest id)."""
    pending = (
        select(Query.assigned_to_id, func.count().label("open"))
        .where(Query.answered_at.is_(None), Query.assigned_to_id.is_not(None))
        .group_by(Query.assigned_to_id)
        .subquery()
    )
    q = (
        _active_team()
        .outerjoin(pending, pending.c.assigned_to_id == User.id)
        .order_by(func.coalesce(pending.c.open, 0), User.id)
        .limit(1)
    )
    return await db.scalar(q)


async def pick_member(db: AsyncSession, farmer_id: int) -> int | None:
    return await sticky_member(db, farmer_id) or await least_busy_member(db)
