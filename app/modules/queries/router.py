from fastapi import APIRouter, File, Form, UploadFile
from fastapi import Query as QueryParam

from app.core.deps import CurrentUser
from app.db.session import DB
from app.modules.queries import service
from app.modules.queries.schemas import QueryOut, QueryPage, ResponseOut

router = APIRouter(prefix="/query", tags=["queries"])


def _removes(remove_text: bool, remove_image: bool, remove_voice: bool, remove_video: bool) -> dict[str, bool]:
    """Collect the 'clear this field' flags sent with an edit."""
    return {"text": remove_text, "image": remove_image, "voice": remove_voice, "video": remove_video}


# ---------------------------------------------------------------- queries (farmer)

@router.post("/upload/", response_model=QueryOut, status_code=201)
async def upload_query(
    user: CurrentUser,
    db: DB,
    text: str | None = Form(None),
    image: UploadFile | None = File(None),
    voice: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
):
    """Ask a question (text and/or image, voice, video); it is auto-assigned to the team."""
    return await service.create_query(db, user, text, image, voice, video)


@router.get("/list/", response_model=QueryPage)
async def list_queries(
    user: CurrentUser,
    db: DB,
    status: service.Status | None = None,
    page: int = QueryParam(1, ge=1),
    page_size: int = QueryParam(10, ge=1, le=100),
):
    """Farmer: own queries. Team member: assigned to them. Admin: all."""
    return await service.list_queries(db, user, status, page, page_size)


@router.put("/update/{query_id}/", response_model=QueryOut, operation_id="update_query_put")
@router.patch("/update/{query_id}/", response_model=QueryOut, operation_id="update_query_patch")
async def update_query(
    query_id: int,
    user: CurrentUser,
    db: DB,
    text: str | None = Form(None),
    image: UploadFile | None = File(None),
    voice: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
    remove_text: bool = Form(False),
    remove_image: bool = Form(False),
    remove_voice: bool = Form(False),
    remove_video: bool = Form(False),
):
    """Owner edits a still-pending query: not sent = keep, new value = replace, remove_x = clear."""
    return await service.update_query(
        db, user, query_id, text,
        service.pick_files(image, voice, video),
        _removes(remove_text, remove_image, remove_voice, remove_video),
    )


# ---------------------------------------------------------------- responses (team)

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
    """The assigned team member (or an admin) answers a query, once."""
    return await service.respond(db, user, query_id, text, image, voice, video)


@router.get("/query-response/{query_id}/", response_model=list[ResponseOut])
async def query_responses(query_id: int, user: CurrentUser, db: DB):
    """A query's answer, for its owner, the assigned member or an admin (others: 404)."""
    query = await service.get_visible_query(db, user, query_id)
    return [query.response] if query.response else []


@router.put("/respond/update/{response_id}/", response_model=ResponseOut, operation_id="update_response_put")
@router.patch("/respond/update/{response_id}/", response_model=ResponseOut, operation_id="update_response_patch")
async def update_response(
    response_id: int,
    user: CurrentUser,
    db: DB,
    text: str | None = Form(None),
    image: UploadFile | None = File(None),
    voice: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
    remove_text: bool = Form(False),
    remove_image: bool = Form(False),
    remove_voice: bool = Form(False),
    remove_video: bool = Form(False),
):
    """A team member edits their own answer (admins: any answer)."""
    return await service.update_response(
        db, user, response_id, text,
        service.pick_files(image, voice, video),
        _removes(remove_text, remove_image, remove_voice, remove_video),
    )
