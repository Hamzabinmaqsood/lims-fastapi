from app.modules.queries import service
from tests.test_farms import login_as

IMG = ("leaf.jpg", b"fake-jpeg", "image/jpeg")


def fake_uploads(monkeypatch):
    async def fake(file, folder, kind):
        return f"https://res.cloudinary.com/demo/{kind}/{file.filename}"
    monkeypatch.setattr(service, "upload_media", fake)


async def test_text_only_query(client):
    h = await login_as(client, "03001111111")
    r = await client.post("/api/query/upload/", headers=h, data={"text": "Leaves turning yellow"})
    assert r.status_code == 201
    assert r.json()["text"] == "Leaves turning yellow"
    assert r.json()["is_done"] is False


async def test_query_with_image(client, monkeypatch):
    fake_uploads(monkeypatch)
    h = await login_as(client, "03001111111")
    r = await client.post("/api/query/upload/", headers=h, files={"image": IMG})
    assert r.status_code == 201
    assert r.json()["image_url"].endswith("/image/leaf.jpg")


async def test_empty_query_400(client):
    h = await login_as(client, "03001111111")
    r = await client.post("/api/query/upload/", headers=h, data={"text": "   "})
    assert r.status_code == 400


async def test_wrong_file_type_400(client):
    h = await login_as(client, "03001111111")
    r = await client.post("/api/query/upload/", headers=h,
                          files={"image": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400  # rejected before any Cloudinary call


async def test_list_only_mine_with_status_and_pages(client):
    me = await login_as(client, "03001111111")
    other = await login_as(client, "03002222222")
    for i in range(3):
        await client.post("/api/query/upload/", headers=me, data={"text": f"q{i}"})
    await client.post("/api/query/upload/", headers=other, data={"text": "not mine"})

    r = await client.get("/api/query/list/", headers=me, params={"page_size": 2})
    body = r.json()
    assert body["count"] == 3                                   # only my queries
    assert [q["text"] for q in body["results"]] == ["q2", "q1"]  # newest first, 2 per page

    r = await client.get("/api/query/list/", headers=me, params={"status": "answered"})
    assert r.json()["count"] == 0
