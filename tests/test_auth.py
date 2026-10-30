from sqlalchemy import select

from app.modules.users.models import User
from tests.conftest import TestSession

USER = {"username": "Hamza", "mobile_number": "03001234567", "password": "secret123","province_id":1, "district_id": 1, "tehsil_id":1,  "locality_id": 1,}


async def signup_and_login(client) -> dict:
    await client.post("/api/user/signup/", json=USER)
    r = await client.post("/api/token/", json={"mobile_number": USER["mobile_number"],
                                               "password": USER["password"]})
    return r.json()


# ---------- signup ----------
async def test_signup_creates_user(client):
    r = await client.post("/api/user/signup/", json=USER)
    assert r.status_code == 201
    assert r.json()["username"] == "hamza"  # lower-cased


async def test_password_is_hashed(client):
    await client.post("/api/user/signup/", json=USER)
    async with TestSession() as db:
        user = await db.scalar(select(User))
    assert user.password != USER["password"]
    assert user.password.startswith("$2b$")


async def test_duplicate_mobile_returns_400(client):
    await client.post("/api/user/signup/", json=USER)
    r = await client.post("/api/user/signup/", json=USER)
    assert r.status_code == 400


async def test_bad_mobile_returns_422(client):
    r = await client.post("/api/user/signup/", json={**USER, "mobile_number": "123"})
    assert r.status_code == 422


# ---------- login ----------
async def test_login_returns_tokens(client):
    data = await signup_and_login(client)
    assert {"access", "refresh", "user_id", "user_role", "user_name"} <= data.keys()
    assert data["user_role"] == "Farmer"


async def test_login_wrong_password_401(client):
    await client.post("/api/user/signup/", json=USER)
    r = await client.post("/api/token/", json={"mobile_number": USER["mobile_number"],
                                               "password": "wrong"})
    assert r.status_code == 401


# ---------- protected endpoint ----------
async def test_verify_without_token_401(client):
    r = await client.get("/api/verify-token/")
    assert r.status_code == 401


async def test_verify_with_access_token_200(client):
    tokens = await signup_and_login(client)
    r = await client.get("/api/verify-token/",
                         headers={"Authorization": f"Bearer {tokens['access']}"})
    assert r.status_code == 200


async def test_refresh_token_cannot_be_used_as_access(client):
    tokens = await signup_and_login(client)
    r = await client.get("/api/verify-token/",
                         headers={"Authorization": f"Bearer {tokens['refresh']}"})
    assert r.status_code == 401


async def test_refresh_gives_new_pair(client):
    tokens = await signup_and_login(client)
    r = await client.post("/api/token/refresh/", json={"refresh": tokens["refresh"]})
    assert r.status_code == 200
    assert "access" in r.json()

async def test_signup_mismatched_location_returns_400(client):
    r = await client.post("/api/user/signup/", json={**USER, "locality_id": 999})
    assert r.status_code == 400

async def auth_headers(client) -> dict:
    tokens = await signup_and_login(client)
    return {"Authorization": f"Bearer {tokens['access']}"}


async def test_profile_completion_increases(client):
    h = await auth_headers(client)
    r = await client.get("/api/user/profile/", headers=h)
    assert r.json()["profile_completion"] == 50  # username + mobile + locality

    r = await client.patch("/api/user/profile/details/", headers=h, data={"cnic": "3520212345671"})
    assert r.json()["profile_completion"] == 70


async def test_signup_with_reference_code(client):
    first = await client.post("/api/user/signup/", json=USER)
    h = await auth_headers(client)
    code = (await client.get("/api/user/profile/", headers=h)).json()["reference_code"]

    r = await client.post("/api/user/signup/", json={
        **USER, "mobile_number": "03009999999", "reference_code": code,
    })
    assert r.status_code == 201


async def test_signup_with_bad_reference_code_400(client):
    r = await client.post("/api/user/signup/", json={**USER, "reference_code": "NOPE1234"})
    assert r.status_code == 400


async def test_signup_wrong_district_for_tehsil_400(client):
    r = await client.post("/api/user/signup/", json={**USER, "district_id": 2})
    assert r.status_code == 400

async def test_details_with_picture(client, monkeypatch):
    async def fake_upload(file, folder):
        return "https://res.cloudinary.com/demo/image/upload/fake.jpg"

    monkeypatch.setattr("app.modules.accounts.service.upload_image", fake_upload)
    h = await auth_headers(client)

    r = await client.patch(
        "/api/user/profile/details/",
        headers=h,
        data={"cnic": "3520212345671", "email": "hamza@test.com"},
        files={"profile_picture": ("me.jpg", b"fakebytes", "image/jpeg")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["profile_picture"].startswith("https://")
    assert body["profile_completion"] == 100


async def test_details_bad_cnic_422(client):
    h = await auth_headers(client)
    r = await client.patch("/api/user/profile/details/", headers=h, data={"cnic": "123"})
    assert r.status_code == 422
