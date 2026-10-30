from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

from app.modules.accounts.router import router as accounts_router

from app.modules.auth.router import router as auth_router
from app.modules.locations.router import router as locations_router
from app.modules.crops.router import router as crops_router
from app.modules.farms.router import router as farms_router


app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url=f"{settings.API_PREFIX}/docs",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
)



app.include_router(accounts_router, prefix=settings.API_PREFIX)
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(locations_router, prefix=settings.API_PREFIX)
app.include_router(crops_router, prefix=settings.API_PREFIX)
app.include_router(farms_router, prefix=settings.API_PREFIX)


@app.get(f"{settings.API_PREFIX}/health/db")
async def health_db(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(text("SELECT version()"))
    return {"database": result.scalar()}
