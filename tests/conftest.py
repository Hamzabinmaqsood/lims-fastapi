import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.db.models  # noqa: F401  (registers all tables in Base.metadata)
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.users.models import Role

TEST_DB = "postgresql+asyncpg://postgres:root@localhost:5432/lims_test"
engine = create_async_engine(TEST_DB, poolclass=NullPool)
TestSession = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def fresh_db():
    """Before EVERY test: empty tables + the 3 roles."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            insert(Role), [{"name": n} for n in ("Farmer", "Response_Team", "SuperAdmin")]
        )
        await conn.execute(text(
            "INSERT INTO provinces (id, name, latitude, longitude) VALUES (1, 'Punjab', 31.17, 72.70);"
        ))
        await conn.execute(text(
            "INSERT INTO districts (id, province_id, name, latitude, longitude) VALUES (1, 1, 'Lahore', 31.52, 74.35);"
        ))
        await conn.execute(text(
            "INSERT INTO tehsils (id, district_id, name, latitude, longitude) VALUES (1, 1, 'Lahore City', 31.54, 74.34);"
        ))
        await conn.execute(text(
            "INSERT INTO localities (id, tehsil_id, name, kind, latitude, longitude) VALUES (1, 1, 'Lahore', 'city', 31.52, 74.35);"
        ))


async def get_test_db():
    async with TestSession() as session:
        yield session


@pytest.fixture
async def client():
    """An HTTP client that calls the app directly (no running server needed)."""
    app.dependency_overrides[get_db] = get_test_db  # swap the real DB for the test DB
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
