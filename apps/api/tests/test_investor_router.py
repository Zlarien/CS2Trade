import httpx
import pytest_asyncio
from fastapi.testclient import TestClient

import dependencies
from db.models import User
from main import app

FREE_STEAMID64 = "76561198000000001"
PREMIUM_STEAMID64 = "76561198000000002"

INVENTORY_RESPONSE = {
    "success": 1,
    "assets": [{"assetid": "111", "classid": "c1", "instanceid": "0", "amount": "1"}],
    "descriptions": [
        {
            "classid": "c1",
            "instanceid": "0",
            "market_hash_name": "MAG-7 | Heaven Guard (Field-Tested)",
            "tradable": 1,
            "marketable": 1,
        }
    ],
    "more_items": 0,
}

SKINPORT_RESPONSE = [
    {
        "market_hash_name": "MAG-7 | Heaven Guard (Field-Tested)",
        "currency": "EUR",
        "median_price": 3.5,
        "quantity": 42,
    }
]


def _steam_handler(request: httpx.Request) -> httpx.Response:
    if request.url.host == "steamcommunity.com" and "/inventory/" in request.url.path:
        return httpx.Response(200, json=INVENTORY_RESPONSE)
    if request.url.host == "api.skinport.com":
        return httpx.Response(200, json=SKINPORT_RESPONSE)
    raise AssertionError(f"unexpected request to {request.url}")


class _FakeLLMProvider:
    async def complete(self, *, system: str, user_message: str, model: str) -> str:
        return "Conseil de test."


@pytest_asyncio.fixture(autouse=True)
async def _seed_users(db_sessionmaker):
    async with db_sessionmaker() as session:
        session.add(User(steamid64=FREE_STEAMID64, tier="free"))
        session.add(User(steamid64=PREMIUM_STEAMID64, tier="premium"))
        await session.commit()


def _make_client(db_sessionmaker, steamid64: str) -> TestClient:
    async def override_db_session():
        async with db_sessionmaker() as session:
            yield session

    async def override_http_client():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_steam_handler)) as c:
            yield c

    app.dependency_overrides[dependencies.get_db_session] = override_db_session
    app.dependency_overrides[dependencies.get_http_client] = override_http_client
    app.dependency_overrides[dependencies.get_current_steamid64] = lambda: steamid64
    app.dependency_overrides[dependencies.get_llm_provider] = lambda: _FakeLLMProvider()
    return TestClient(app)


def test_free_tier_is_blocked(db_sessionmaker) -> None:
    client = _make_client(db_sessionmaker, FREE_STEAMID64)
    try:
        response = client.post("/me/investor-advice", json={})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_premium_tier_gets_advice(db_sessionmaker) -> None:
    client = _make_client(db_sessionmaker, PREMIUM_STEAMID64)
    try:
        response = client.post("/me/investor-advice", json={"question": "Que faire ?"})
        assert response.status_code == 200
        body = response.json()
        assert body["summary"] == "Conseil de test."
        assert body["model"]
    finally:
        app.dependency_overrides.clear()


def test_investor_advice_requires_auth() -> None:
    app.dependency_overrides.clear()
    client = TestClient(app)
    response = client.post("/me/investor-advice", json={})
    assert response.status_code == 401
