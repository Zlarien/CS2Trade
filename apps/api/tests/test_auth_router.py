import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import dependencies
from auth.session import SESSION_COOKIE_NAME
from db.models import User
from main import app

VALID_CLAIMED_ID = "https://steamcommunity.com/openid/id/76561198034202275"


def _handler_valid(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text="is_valid:true\n")


def _handler_invalid(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text="is_valid:false\n")


@pytest.fixture
def client(db_sessionmaker, fake_redis):
    async def override_db_session():
        async with db_sessionmaker() as session:
            yield session

    async def override_http_client_valid():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler_valid)) as c:
            yield c

    app.dependency_overrides[dependencies.get_db_session] = override_db_session
    app.dependency_overrides[dependencies.get_http_client] = override_http_client_valid
    app.dependency_overrides[dependencies.get_redis_client] = lambda: fake_redis
    try:
        yield TestClient(app, follow_redirects=False)
    finally:
        app.dependency_overrides.clear()


def test_login_redirects_to_steam(client: TestClient) -> None:
    response = client.get("/auth/steam/login")
    assert response.status_code in (302, 307)
    assert response.headers["location"].startswith("https://steamcommunity.com/openid/login")


def test_callback_creates_user_and_sets_session_cookie(
    client: TestClient, db_sessionmaker
) -> None:
    response = client.get(
        "/auth/steam/callback",
        params={"openid.claimed_id": VALID_CLAIMED_ID, "openid.mode": "id_res"},
    )

    assert response.status_code in (302, 307)
    assert SESSION_COOKIE_NAME in response.cookies


@pytest.mark.asyncio
async def test_callback_persists_user_in_db(client: TestClient, db_sessionmaker) -> None:
    client.get(
        "/auth/steam/callback",
        params={"openid.claimed_id": VALID_CLAIMED_ID, "openid.mode": "id_res"},
    )

    async with db_sessionmaker() as session:
        result = await session.execute(select(User).where(User.steamid64 == "76561198034202275"))
        assert result.scalar_one_or_none() is not None


def test_callback_rejects_invalid_signature(db_sessionmaker, fake_redis) -> None:
    async def override_db_session():
        async with db_sessionmaker() as session:
            yield session

    async def override_http_client_invalid():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler_invalid)) as c:
            yield c

    app.dependency_overrides[dependencies.get_db_session] = override_db_session
    app.dependency_overrides[dependencies.get_http_client] = override_http_client_invalid
    app.dependency_overrides[dependencies.get_redis_client] = lambda: fake_redis
    try:
        client = TestClient(app)
        response = client.get(
            "/auth/steam/callback",
            params={"openid.claimed_id": VALID_CLAIMED_ID, "openid.mode": "id_res"},
        )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_logout_clears_cookie(client: TestClient) -> None:
    response = client.post("/auth/steam/logout")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
