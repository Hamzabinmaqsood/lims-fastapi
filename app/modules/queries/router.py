from fastapi import APIRouter, File, Form, Query as QueryParam, UploadFile

from app.core.deps import CurrentUser
from app.db.session import DB
from app.modules.queries import service
from app.modules.queries.schemas import QueryOut, QueryPage, ResponseOut

router = APIRouter(prefix="/query", tags=["queries"])


@router.post("/upload/", response_model=QueryOut, status_code=201)
async def upload_query(
    user: CurrentUser,
    db: DB,
    text: str | None = Form(None),
    image: UploadFile | None = File(None),
    voice: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
):
    return await service.create_query(db, user, text, image, voice, video)


@router.get("/list/", response_model=QueryPage)
async def list_queries(
    user: CurrentUser,
    db: DB,
    status: service.Status | None = None,
    page: int = QueryParam(1, ge=1),
    page_size: int = QueryParam(10, ge=1, le=100),
):
    return await service.list_queries(db, user, status, page, page_size)



@router.post("/respond/{query_id}/", response_model=ResponseOut, status_code=201)
async def respond(
    query_id: int,
    user: CurrentUser,
    db: DB,
    text: str | None = Form(None),
    image: UploadFile | None = File(None),
    voice: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
):
    return await service.respond(db, user, query_id, text, image, voice, video)


@router.get("/query-response/{query_id}/", response_model=list[ResponseOut])
async def query_responses(query_id: int, user: CurrentUser, db: DB):
    query = await service.get_visible_query(db, user, query_id)
    return [query.response] if query.response else []
