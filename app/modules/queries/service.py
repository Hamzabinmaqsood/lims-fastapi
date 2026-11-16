import asyncio
from typing import Literal

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import upload_media
from app.modules.queries.models import Query
from app.modules.users.models import User

from datetime import UTC, datetime

from app.modules.queries.assignment import pick_member

from datetime import UTC, datetime

from app.modules.queries.models import Query, QueryResponse
from app.modules.users.models import ROLE_RESPONSE_TEAM, ROLE_SUPER_ADMIN, User

Status = Literal["pending", "answered"]


async def create_query(
    db: AsyncSession,
    user: User,
    text: str | None,
    image: UploadFile | None,
    voice: UploadFile | None,
    video: UploadFile | None,
) -> Query:
    text = (text or "").strip() or None
    files = {"image": image, "voice": voice, "video": video}
    files = _pick_files(image, voice, video)
    if text is None and not files:
        raise HTTPException(400, {"error": "Send a text, image, voice note or video."})


    # Upload all attachments at the same time.
    urls = await asyncio.gather(
        *(upload_media(f, f"lims/queries/{user.id}", kind) for kind, f in files.items())
    )
    media = await _upload(files, f"lims/queries/{user.id}")

    query = Query(
        user_id=user.id,
        text=text,
        image_url=media.get("image"),
        voice_url=media.get("voice"),
        video_url=media.get("video"),
    )
    member_id = await pick_member(db, user.id)
    if member_id is not None:
        query.assigned_to_id = member_id
        query.assigned_at = datetime.now(UTC)
    db.add(query)
    await db.commit()
    await db.refresh(query)
    return query


def _visible_to(user: User):
    """Which queries this user may list."""
    q = select(Query)
    if is_admin(user):
        return q
    if user.role.name == ROLE_RESPONSE_TEAM:
        return q.where(Query.assigned_to_id == user.id)
    return q.where(Query.user_id == user.id)


async def list_queries(db: AsyncSession, user: User, status: Status | None, page: int, page_size: int) -> dict:
    q = _visible_to(user)
    if status == "pending":
        q = q.where(Query.answered_at.is_(None))
    elif status == "answered":
        q = q.where(Query.answered_at.is_not(None))

    count = await db.scalar(select(func.count()).select_from(q.subquery()))
    rows = await db.scalars(
        q.order_by(Query.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return {"count": count, "page": page, "page_size": page_size, "results": list(rows.all())}


def is_admin(user: User) -> bool:
    return user.is_superuser or user.role.name == ROLE_SUPER_ADMIN


def is_responder(user: User) -> bool:
    return is_admin(user) or user.role.name == ROLE_RESPONSE_TEAM


def _pick_files(image, voice, video) -> dict[str, UploadFile]:
    files = {"image": image, "voice": voice, "video": video}
    return {kind: f for kind, f in files.items() if f is not None and f.filename}


async def _upload(files: dict[str, UploadFile], folder: str) -> dict[str, str]:
    urls = await asyncio.gather(*(upload_media(f, folder, kind) for kind, f in files.items()))
    return dict(zip(files, urls))



#Answering Queries Logic
def _check_can_answer(user: User, query: Query) -> None:
    if query.is_done:
        raise HTTPException(400, {"error": "Query already answered"})
    if query.assigned_to_id not in (None, user.id) and not is_admin(user):
        raise HTTPException(403, {"error": "This query is assigned to another team member."})


async def respond(
    db: AsyncSession, user: User, query_id: int,
    text: str | None, image: UploadFile | None, voice: UploadFile | None, video: UploadFile | None,
) -> QueryResponse:
    if not is_responder(user):
        raise HTTPException(403, {"error": "Only the response team can answer queries."})
    text = (text or "").strip() or None
    files = _pick_files(image, voice, video)
    if text is None and not files:
        raise HTTPException(400, {"error": "Send a text, image, voice note or video."})

    # 1. Fast checks, no lock.
    query = await db.get(Query, query_id)
    if query is None:
        raise HTTPException(404, {"error": "Query not found"})
    _check_can_answer(user, query)

    # 2. Slow work, no lock held.
    media = await _upload(files, f"lims/responses/{query_id}")

    # 3. Lock the row and check again: someone may have answered while we uploaded.
    query = await db.scalar(
        select(Query).where(Query.id == query_id).with_for_update()
        .execution_options(populate_existing=True)
    )
    _check_can_answer(user, query)

    now = datetime.now(UTC)
    if query.assigned_to_id is None:  # unassigned → the responder takes it
        query.assigned_to_id, query.assigned_at = user.id, now
    query.answered_at = now
    response = QueryResponse(
        query_id=query.id,
        responder_id=user.id,
        text=text,
        image_url=media.get("image"),
        voice_url=media.get("voice"),
        video_url=media.get("video"),
    )
    db.add(response)
    await db.commit()  # the commit also releases the lock
    await db.refresh(response)
    return response


async def get_visible_query(db: AsyncSession, user: User, query_id: int) -> Query:
    """Owner, assigned member or admin — everyone else sees 404 (no IDOR)."""
    query = await db.get(Query, query_id)
    if query is None or not (
        query.user_id == user.id or query.assigned_to_id == user.id or is_admin(user)
    ):
        raise HTTPException(404, {"error": "Query not found"})
    return query
