"""Queries: farmers ask, the response team answers."""

import asyncio
from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import upload_media
from app.modules.queries.assignment import pick_member
from app.modules.queries.models import Query, QueryResponse, QueryVersion, ResponseVersion
from app.modules.users.models import ROLE_RESPONSE_TEAM, ROLE_SUPER_ADMIN, User

Status = Literal["pending", "answered"]
KINDS = ("image", "voice", "video")


# ---------------------------------------------------------------- roles

def is_admin(user: User) -> bool:
    """Superuser or SuperAdmin role."""
    return user.is_superuser or user.role.name == ROLE_SUPER_ADMIN


def is_responder(user: User) -> bool:
    """May answer queries: Response_Team or an admin."""
    return is_admin(user) or user.role.name == ROLE_RESPONSE_TEAM


# ---------------------------------------------------------------- media helpers

def pick_files(image, voice, video) -> dict[str, UploadFile]:
    """Keep only the files that were really sent (Swagger sends empty fields)."""
    files = {"image": image, "voice": voice, "video": video}
    return {kind: f for kind, f in files.items() if f is not None and f.filename}


async def _upload(files: dict[str, UploadFile], folder: str) -> dict[str, str]:
    """Upload all files at the same time; returns {kind: url}."""
    urls = await asyncio.gather(*(upload_media(f, folder, kind) for kind, f in files.items()))
    return dict(zip(files, urls))


def _would_be_empty(obj, text: str | None, files: dict, removes: dict[str, bool]) -> bool:
    """Would this edit leave no text and no media? Checked BEFORE uploading."""
    if removes.get("text"):
        new_text = None
    else:
        new_text = obj.text if text is None else (text.strip() or None)
    has_media = any(
        kind in files or (getattr(obj, f"{kind}_url") and not removes[kind]) for kind in KINDS
    )
    return new_text is None and not has_media


def _apply_edits(obj, text: str | None, media: dict[str, str], removes: dict[str, bool]) -> None:
    """not sent = keep, new value = replace, remove flag = clear."""
    if removes.get("text"):
        obj.text = None
    elif text is not None:
        obj.text = text.strip() or None
    for kind in KINDS:
        if kind in media:
            setattr(obj, f"{kind}_url", media[kind])
        elif removes[kind]:
            setattr(obj, f"{kind}_url", None)


def _content(obj) -> dict:
    """The 4 content fields of a query or answer, as a dict."""
    return {"text": obj.text, "image_url": obj.image_url,
            "voice_url": obj.voice_url, "video_url": obj.video_url}
# ---------------------------------------------------------------- asking (Q1 + Q2)

async def create_query(
    db: AsyncSession,
    user: User,
    text: str | None,
    image: UploadFile | None,
    voice: UploadFile | None,
    video: UploadFile | None,
) -> Query:
    """Save a farmer's question and auto-assign it to a team member."""
    text = (text or "").strip() or None
    files = pick_files(image, voice, video)
    if text is None and not files:
        raise HTTPException(400, {"error": "Send a text, image, voice note or video."})

    media = await _upload(files, f"lims/queries/{user.id}")
    query = Query(
        user_id=user.id,
        text=text,
        image_url=media.get("image"),
        voice_url=media.get("voice"),
        video_url=media.get("video"),
    )

    member_id = await pick_member(db)
    if member_id is not None:
        query.assigned_to_id = member_id
        query.assigned_at = datetime.now(UTC)

    db.add(query)
    await db.commit()
    await db.refresh(query)
    return query


# ---------------------------------------------------------------- listing (Q3)

def _visible_to(user: User):
    """Which queries this user may list."""
    q = select(Query)
    if is_admin(user):
        return q
    if user.role.name == ROLE_RESPONSE_TEAM:
        return q.where(Query.assigned_to_id == user.id)
    return q.where(Query.user_id == user.id)


async def list_queries(
    db: AsyncSession, user: User, status: Status | None, page: int, page_size: int
) -> dict:
    """One page of the queries this user may see, newest first."""
    q = _visible_to(user)
    if status is not None:
        q = q.where(Query.status == status)

    count = await db.scalar(select(func.count()).select_from(q.subquery()))
    rows = await db.scalars(
        q.order_by(Query.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return {"count": count, "page": page, "page_size": page_size, "results": list(rows.all())}


async def get_visible_query(db: AsyncSession, user: User, query_id: int) -> Query:
    """Owner, assigned member or admin — everyone else sees 404 (no IDOR)."""
    query = await db.get(Query, query_id)
    if query is None or not (
        query.user_id == user.id or query.assigned_to_id == user.id or is_admin(user)
    ):
        raise HTTPException(404, {"error": "Query not found"})
    return query


# ---------------------------------------------------------------- answering (Q3)

def _check_can_answer(user: User, query: Query) -> None:
    """Not answered yet, and assigned to this user (or unassigned, or user is admin)."""
    if query.is_done:
        raise HTTPException(400, {"error": "Query already answered"})
    if query.assigned_to_id not in (None, user.id) and not is_admin(user):
        raise HTTPException(403, {"error": "This query is assigned to another team member."})


async def _locked_query(db: AsyncSession, query_id: int) -> Query:
    """Re-read the query with a row lock (SELECT ... FOR UPDATE), fresh values."""
    return await db.scalar(
        select(Query).where(Query.id == query_id).with_for_update()
        .execution_options(populate_existing=True)
    )


async def respond(
    db: AsyncSession,
    user: User,
    query_id: int,
    text: str | None,
    image: UploadFile | None,
    voice: UploadFile | None,
    video: UploadFile | None,
) -> QueryResponse:
    """Answer a query once: check → upload (no lock) → lock + re-check → save."""
    if not is_responder(user):
        raise HTTPException(403, {"error": "Only the response team can answer queries."})
    text = (text or "").strip() or None
    files = pick_files(image, voice, video)
    if text is None and not files:
        raise HTTPException(400, {"error": "Send a text, image, voice note or video."})

    query = await db.get(Query, query_id)
    if query is None:
        raise HTTPException(404, {"error": "Query not found"})
    _check_can_answer(user, query)

    media = await _upload(files, f"lims/responses/{query_id}")

    query = await _locked_query(db, query_id)
    _check_can_answer(user, query)

    now = datetime.now(UTC)
    if query.assigned_to_id is None:  # unassigned → the responder takes it
        query.assigned_to_id, query.assigned_at = user.id, now
    query.answered_at = now
    query.status = "answered"
    response = QueryResponse(
        query_id=query.id,
        responder_id=user.id,
        text=text,
        image_url=media.get("image"),
        voice_url=media.get("voice"),
        video_url=media.get("video"),
    )
    db.add(response)
    await db.commit()  # also releases the lock
    await db.refresh(response)
    return response


# ---------------------------------------------------------------- editing (Q4)

async def update_query(
    db: AsyncSession, user: User, query_id: int,
    text: str | None, files: dict[str, UploadFile], removes: dict[str, bool],
) -> Query:
    """The owner edits a still-pending query."""
    query = await db.get(Query, query_id)
    if query is None or query.user_id != user.id:
        raise HTTPException(404, {"error": "Query not found"})
    if query.is_done:
        raise HTTPException(400, {"error": "An answered query can't be edited."})
    if _would_be_empty(query, text, files, removes):
        raise HTTPException(400, {"error": "A query can't be empty."})

    media = await _upload(files, f"lims/queries/{user.id}")

    query = await _locked_query(db, query_id)  # it may have been answered meanwhile
    if query.is_done:
        raise HTTPException(400, {"error": "An answered query can't be edited."})

    before = _content(query)
    _apply_edits(query, text, media, removes)
    if _content(query) != before:                       # only if something really changed
        db.add(QueryVersion(query_id=query.id, **before))
    await db.commit()
    await db.refresh(query)
    return query


async def update_response(
    db: AsyncSession, user: User, response_id: int,
    text: str | None, files: dict[str, UploadFile], removes: dict[str, bool],
) -> QueryResponse:
    """A team member edits their own answer (admins: any answer)."""
    response = await db.get(QueryResponse, response_id)
    if response is None or not is_responder(user):
        raise HTTPException(404, {"error": "Response not found"})
    if response.responder_id != user.id and not is_admin(user):
        raise HTTPException(403, {"error": "You can only edit your own answers."})
    if _would_be_empty(response, text, files, removes):
        raise HTTPException(400, {"error": "An answer can't be empty."})

    media = await _upload(files, f"lims/responses/{response.query_id}")
    before = _content(response)
    _apply_edits(response, text, media, removes)
    if _content(response) != before:
        db.add(ResponseVersion(response_id=response.id, **before))
        response.status = "edited"
    await db.commit()
    await db.refresh(response)
    return response
