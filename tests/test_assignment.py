from sqlalchemy import text

from tests.conftest import engine
from tests.test_farms import login_as


async def make_team_member(client, mobile: str) -> int:
    await login_as(client, mobile)  # signs up + logs in
    async with engine.begin() as conn:
        await conn.execute(text(
            "UPDATE users SET role_id = (SELECT id FROM roles WHERE name = 'Response_Team') "
            f"WHERE mobile_number = '{mobile}'"
        ))
        return await conn.scalar(text(f"SELECT id FROM users WHERE mobile_number = '{mobile}'"))


async def ask(client, headers, text_: str = "help") -> dict:
    return (await client.post("/api/query/upload/", headers=headers, data={"text": text_})).json()


async def test_no_team_means_unassigned(client):
    farmer = await login_as(client, "03001111111")
    assert (await ask(client, farmer))["assigned_to_id"] is None


async def test_balanced_picks_least_busy(client):
    a = await make_team_member(client, "03100000001")
    b = await make_team_member(client, "03100000002")
    f1 = await login_as(client, "03001111111")
    f2 = await login_as(client, "03002222222")
    assert (await ask(client, f1))["assigned_to_id"] == a   # tie → lowest id
    assert (await ask(client, f2))["assigned_to_id"] == b   # a has 1 pending, b has 0


async def test_same_farmer_goes_to_least_busy_not_previous(client):
    a = await make_team_member(client, "03100000001")
    b = await make_team_member(client, "03100000002")
    farmer = await login_as(client, "03001111111")
    assert (await ask(client, farmer))["assigned_to_id"] == a   # tie → lowest id
    assert (await ask(client, farmer))["assigned_to_id"] == b   # no sticky: b has fewer


async def test_answered_queries_do_not_count_as_load(client):
    a = await make_team_member(client, "03100000001")
    await make_team_member(client, "03100000002")
    f1 = await login_as(client, "03001111111")
    await ask(client, f1)  # goes to a
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE queries SET answered_at = now(), status = 'answered'"))
    f2 = await login_as(client, "03002222222")
    assert (await ask(client, f2))["assigned_to_id"] == a   # a has 0 PENDING → tie → lowest id
