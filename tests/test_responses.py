from tests.test_assignment import ask, make_team_member
from tests.test_farms import login_as


async def setup(client):
    """Team members a (gets the query) and b; one farmer query assigned to a."""
    a = await make_team_member(client, "03100000001")
    await make_team_member(client, "03100000002")
    farmer = await login_as(client, "03001111111")
    query = await ask(client, farmer, "Yellow leaves?")
    team_a = await login_as(client, "03100000001")
    team_b = await login_as(client, "03100000002")
    return farmer, team_a, team_b, query, a


async def answer(client, headers, query_id, text_="Use nitrogen fertilizer"):
    return await client.post(f"/api/query/respond/{query_id}/", headers=headers, data={"text": text_})


async def test_assigned_member_answers(client):
    farmer, team_a, _, query, a = await setup(client)
    r = await answer(client, team_a, query["id"])
    assert r.status_code == 201
    assert r.json()["responder_id"] == a

    mine = (await client.get("/api/query/list/", headers=farmer)).json()["results"][0]
    assert mine["is_done"] is True
    assert mine["response"]["text"] == "Use nitrogen fertilizer"   # answer shown inline


async def test_cannot_answer_twice(client):
    _, team_a, _, query, _ = await setup(client)
    await answer(client, team_a, query["id"])
    assert (await answer(client, team_a, query["id"])).status_code == 400


async def test_other_member_403(client):
    _, _, team_b, query, _ = await setup(client)
    assert (await answer(client, team_b, query["id"])).status_code == 403


async def test_farmer_cannot_answer_403(client):
    farmer, _, _, query, _ = await setup(client)
    assert (await answer(client, farmer, query["id"])).status_code == 403


async def test_unknown_query_404(client):
    _, team_a, _, _, _ = await setup(client)
    assert (await answer(client, team_a, 999999)).status_code == 404


async def test_empty_answer_400(client):
    _, team_a, _, query, _ = await setup(client)
    assert (await answer(client, team_a, query["id"], "  ")).status_code == 400


async def test_lists_depend_on_role(client):
    farmer, team_a, team_b, query, _ = await setup(client)
    assert (await client.get("/api/query/list/", headers=team_a)).json()["count"] == 1  # assigned to a
    assert (await client.get("/api/query/list/", headers=team_b)).json()["count"] == 0  # not b's
    assert (await client.get("/api/query/list/", headers=farmer)).json()["count"] == 1  # own


async def test_viewing_answers_is_private(client):
    farmer, team_a, _, query, _ = await setup(client)
    await answer(client, team_a, query["id"])
    other_farmer = await login_as(client, "03002222222")

    r = await client.get(f"/api/query/query-response/{query['id']}/", headers=farmer)
    assert r.status_code == 200 and len(r.json()) == 1
    r = await client.get(f"/api/query/query-response/{query['id']}/", headers=other_farmer)
    assert r.status_code == 404
