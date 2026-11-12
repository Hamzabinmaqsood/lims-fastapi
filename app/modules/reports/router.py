from fastapi import APIRouter, Response

from app.core.deps import CurrentUser
from app.db.session import DB
from app.modules.reports import service

router = APIRouter(prefix="/farms", tags=["reports"])


@router.get(
    "/{farm_id}/report/",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def farm_report(farm_id: int, user: CurrentUser, db: DB):
    pdf = await service.report_pdf(db, user, farm_id)
    return Response(
        pdf,
        media_type="application/pdf",
        # inline = open in the browser; "attachment" would force a download
        headers={"Content-Disposition": f'inline; filename="farm-{farm_id}-report.pdf"'},
    )
