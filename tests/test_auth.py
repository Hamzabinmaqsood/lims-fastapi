from sqlalchemy import select

from app.modules.users.models import User
from tests.conftest import TestSession

USER = {"username": "Hamza", "mobile_number": "03001234567", "password": "secret123"}


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
