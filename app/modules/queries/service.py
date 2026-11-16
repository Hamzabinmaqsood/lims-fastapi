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
    files = {kind: f for kind, f in files.items() if f is not None and f.filename}
    if text is None and not files:
        raise HTTPException(400, {"error": "Send a text, image, voice note or video."})

    # Upload all attachments at the same time.
    urls = await asyncio.gather(
        *(upload_media(f, f"lims/queries/{user.id}", kind) for kind, f in files.items())
    )
    media = dict(zip(files, urls))

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


async def list_my_queries(
    db: AsyncSession, user: User, status: Status | None, page: int, page_size: int
) -> dict:
    q = select(Query).where(Query.user_id == user.id)
    if status == "pending":
        q = q.where(Query.answered_at.is_(None))
    elif status == "answered":
        q = q.where(Query.answered_at.is_not(None))

    count = await db.scalar(select(func.count()).select_from(q.subquery()))
    rows = await db.scalars(
        q.order_by(Query.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return {"count": count, "page": page, "page_size": page_size, "results": list(rows.all())}
