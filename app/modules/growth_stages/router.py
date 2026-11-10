from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.deps import AdminUser, CurrentUser
from app.db.session import DB
from app.modules.growth_stages import service
from app.modules.growth_stages.schemas import StageIn, StageOut

MAX_IMPORT_BYTES = 5 * 1024 * 1024  # 5 MB

router = APIRouter(prefix="/growth-stages", tags=["growth stages"])


@router.get("/", response_model=list[StageOut])
async def list_stages(crop_id: int, user: CurrentUser, db: DB):
    return await service.list_stages(db, crop_id)


@router.post("/", response_model=StageOut, status_code=201)
async def create_stage(data: StageIn, admin: AdminUser, db: DB):
    return await service.create_stage(db, data)


@router.put("/{stage_id}/", response_model=StageOut)
async def replace_stage(stage_id: int, data: StageIn, admin: AdminUser, db: DB):
    return await service.replace_stage(db, stage_id, data)


@router.delete("/{stage_id}/", status_code=204)
async def delete_stage(stage_id: int, admin: AdminUser, db: DB) -> None:
    await service.delete_stage(db, stage_id)



@router.post("/import/")
async def import_stages(admin: AdminUser, db: DB, crop_id: int = Form(...), file: UploadFile = File(...),):
    content = await file.read(MAX_IMPORT_BYTES + 1)
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(400, {"file": ["File must be 5 MB or smaller."]})
    return await service.import_stages(db, crop_id, content, file.filename or "")
