"""Pick the Response_Team member for a new query: the one with the fewest assigned queries."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.queries.models import Query
from app.modules.users.models import ROLE_RESPONSE_TEAM, Role, User


async def pick_member(db: AsyncSession) -> int | None:
    """Active team member with the fewest PENDING queries (ties → lowest id); None if no team."""
    load = (
        select(Query.assigned_to_id, func.count().label("n"))
        .where(Query.status == "pending")  # ← remove this line to count ALL assigned queries ever
        .where(Query.assigned_to_id.is_not(None))
        .group_by(Query.assigned_to_id)
        .subquery()
    )
    q = (
        select(User.id)
        .join(Role, User.role_id == Role.id)
        .where(Role.name == ROLE_RESPONSE_TEAM, User.is_active.is_(True))
        .outerjoin(load, load.c.assigned_to_id == User.id)
        .order_by(func.coalesce(load.c.n, 0), User.id)
        .limit(1)
    )
    return await db.scalar(q)
