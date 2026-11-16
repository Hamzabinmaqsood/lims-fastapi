from app.modules.queries import service
from tests.test_assignment import ask, make_team_member
from tests.test_farms import login_as
from tests.test_responses import answer, setup


async def edit_query(client, h, query_id, **data):
    return await client.patch(f"/api/query/update/{query_id}/", headers=h, data=data)


async def test_owner_edits_pending_query(client):
    farmer = await login_as(client, "03001111111")
    q = await ask(client, farmer, "old text")
    r = await edit_query(client, farmer, q["id"], text="new text")
    assert r.status_code == 200 and r.json()["text"] == "new text"


async def test_other_farmer_cannot_edit_404(client):
    farmer = await login_as(client, "03001111111")
    q = await ask(client, farmer)
    other = await login_as(client, "03002222222")
    assert (await edit_query(client, other, q["id"], text="hacked")).status_code == 404


async def test_answered_query_is_locked_400(client):
    farmer, team_a, _, q, _ = await setup(client)
    await answer(client, team_a, q["id"])
    assert (await edit_query(client, farmer, q["id"], text="changed")).status_code == 400


async def test_edit_cannot_empty_the_query_400(client):
    farmer = await login_as(client, "03001111111")
    q = await ask(client, farmer, "only text")
    assert (await edit_query(client, farmer, q["id"], remove_text="true")).status_code == 400


async def test_replace_and_remove_image(client, monkeypatch):
    async def fake(file, folder, kind):
        return f"https://cdn.example/{file.filename}"
    monkeypatch.setattr(service, "upload_media", fake)

    farmer = await login_as(client, "03001111111")
    q = await ask(client, farmer, "with photo")
    r = await client.patch(f"/api/query/update/{q['id']}/", headers=farmer,
                           files={"image": ("new.jpg", b"x", "image/jpeg")})
    assert r.json()["image_url"] == "https://cdn.example/new.jpg"

    r = await edit_query(client, farmer, q["id"], remove_image="true")
    assert r.json()["image_url"] is None and r.json()["text"] == "with photo"


async def test_responder_edits_own_answer_only(client):
    farmer, team_a, team_b, q, _ = await setup(client)
    response_id = (await answer(client, team_a, q["id"])).json()["id"]
    url = f"/api/query/respond/update/{response_id}/"

    r = await client.patch(url, headers=team_a, data={"text": "Better advice"})
    assert r.status_code == 200 and r.json()["text"] == "Better advice"
    assert (await client.patch(url, headers=team_b, data={"text": "x"})).status_code == 403
    assert (await client.patch(url, headers=farmer, data={"text": "x"})).status_code == 404
