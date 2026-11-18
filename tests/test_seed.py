from sqlalchemy import func, select

from app.core.security import verify_password
from app.modules.farms.models import Farm
from app.modules.users.models import User
from scripts.seed import N_FARMERS, N_TEAM, seed
from tests.conftest import TestSession


async def test_seed_creates_users_and_1_to_3_farms(client):
    async with TestSession() as db:
        made = await seed(db, "Demo@12345")
    assert made["farmers"] == N_FARMERS and made["team"] == N_TEAM
    assert N_FARMERS <= made["farms"] <= 3 * N_FARMERS

    async with TestSession() as db:
        per_farmer = (await db.execute(select(func.count()).select_from(Farm).group_by(Farm.owner_id))).scalars().all()
        assert set(per_farmer) <= {1, 2, 3}
        user = await db.scalar(select(User).where(User.mobile_number == "03009000001"))
        assert verify_password("Demo@12345", user.password)


async def test_seed_twice_adds_nothing(client):
    async with TestSession() as db:
        await seed(db, "Demo@12345")
    async with TestSession() as db:
        again = await seed(db, "Demo@12345")
    assert again == {"farmers": 0, "team": 0, "farms": 0}
