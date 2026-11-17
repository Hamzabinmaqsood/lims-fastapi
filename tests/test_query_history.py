from sqlalchemy import func, select

from app.modules.queries.models import QueryVersion, ResponseVersion
from tests.conftest import TestSession
from tests.test_assignment import ask
from tests.test_farms import login_as
from tests.test_responses import answer, setup


async def count(model) -> int:
    async with TestSession() as db:
        return await db.scalar(select(func.count()).select_from(model))


async def test_new_query_is_pending(client):
    farmer = await login_as(client, "03001111111")
    assert (await ask(client, farmer))["status"] == "pending"


async def test_answer_sets_status_answered(client):
    farmer, team_a, _, q, _ = await setup(client)
    r = await answer(client, team_a, q["id"])
    assert r.json()["status"] == "sent"
    mine = (await client.get("/api/query/list/", headers=farmer)).json()["results"][0]
    assert mine["status"] == "answered" and mine["is_done"] is True


async def test_status_filter(client):
    farmer, team_a, _, q, _ = await setup(client)
    await answer(client, team_a, q["id"])
    r = await client.get("/api/query/list/", headers=farmer, params={"status": "pending"})
    assert r.json()["count"] == 0


async def test_query_edit_keeps_old_version(client):
    farmer = await login_as(client, "03001111111")
    q = await ask(client, farmer, "Leaves yellow")
    await client.patch(f"/api/query/update/{q['id']}/", headers=farmer, data={"text": "Leaves yellow with spots"})

    async with TestSession() as db:
        old = await db.scalar(select(QueryVersion))
    assert old.text == "Leaves yellow"            # the previous version is kept
    assert old.query_id == q["id"]


async def test_no_change_no_version(client):
    farmer = await login_as(client, "03001111111")
    q = await ask(client, farmer, "same")
    await client.patch(f"/api/query/update/{q['id']}/", headers=farmer, data={"text": "same"})
    assert await count(QueryVersion) == 0


async def test_answer_edit_keeps_old_version_and_marks_edited(client):
    _, team_a, _, q, _ = await setup(client)
    response_id = (await answer(client, team_a, q["id"], "Use urea")).json()["id"]
    r = await client.patch(f"/api/query/respond/update/{response_id}/", headers=team_a,
                           data={"text": "Use urea, 1 bag per acre"})
    assert r.json()["status"] == "edited"

    async with TestSession() as db:
        old = await db.scalar(select(ResponseVersion))
    assert old.text == "Use urea"
