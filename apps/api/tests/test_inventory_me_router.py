import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

import dependencies
from db.models import ExcludedItem, User
from main import app

STEAMID64 = "76561198034202275"

INVENTORY_RESPONSE = {
    "success": 1,
    "assets": [
        {"assetid": "111", "classid": "c1", "instanceid": "0", "amount": "1"},
        {"assetid": "222", "classid": "c2", "instanceid": "0", "amount": "1"},
    ],
    "descriptions": [
        {
            "classid": "c1",
            "instanceid": "0",
            "market_hash_name": "MAG-7 | Heaven Guard (Field-Tested)",
            "tradable": 1,
            "marketable": 1,
        },
        {
            "classid": "c2",
            "instanceid": "0",
            "market_hash_name": "AK-47 | Redline (Field-Tested)",
            "tradable": 1,
            "marketable": 1,
        },
    ],
    "more_items": 0,
}

SKINPORT_RESPONSE = [
    {
        "market_hash_name": "MAG-7 | Heaven Guard (Field-Tested)",
        "currency": "EUR",
        "median_price": 3.5,
        "quantity": 42,
    },
    {
        "market_hash_name": "AK-47 | Redline (Field-Tested)",
        "currency": "EUR",
        "median_price": 15.0,
        "quantity": 10,
    },
]


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.host == "steamcommunity.com" and "/inventory/" in request.url.path:
        return httpx.Response(200, json=INVENTORY_RESPONSE)
    if request.url.host == "api.skinport.com":
        return httpx.Response(200, json=SKINPORT_RESPONSE)
    raise AssertionError(f"unexpected request to {request.url}")


@pytest_asyncio.fixture(autouse=True)
async def _seed_user(db_sessionmaker):
    async with db_sessionmaker() as session:
        session.add(User(steamid64=STEAMID64))
        await session.commit()


@pytest.fixture
def client(db_sessionmaker):
    async def override_db_session():
        async with db_sessionmaker() as session:
            yield session

    async def override_http_client():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as c:
            yield c

    app.dependency_overrides[dependencies.get_db_session] = override_db_session
    app.dependency_overrides[dependencies.get_http_client] = override_http_client
    app.dependency_overrides[dependencies.get_current_steamid64] = lambda: STEAMID64
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_recommendations_include_all_items_when_nothing_excluded(client: TestClient) -> None:
    response = client.get("/inventory/me/recommendations")

    assert response.status_code == 200
    body = response.json()
    assert body["steamid64"] == STEAMID64
    assert body["item_count"] == 2
    assert body["excluded_count"] == 0
    assert {r["item_id"] for r in body["recommendations"]} == {"111", "222"}


@pytest.mark.asyncio
async def test_excluded_item_is_filtered_before_recommendation(
    client: TestClient, db_sessionmaker
) -> None:
    async with db_sessionmaker() as session:
        session.add(ExcludedItem(user_steamid64=STEAMID64, asset_id="222", reason="cadeau"))
        await session.commit()

    response = client.get("/inventory/me/recommendations")

    assert response.status_code == 200
    body = response.json()
    assert body["excluded_count"] == 1
    item_ids = {r["item_id"] for r in body["recommendations"]}
    assert item_ids == {"111"}
    assert "222" not in item_ids

    # L'item exclu reste visible dans "items" (avec excluded=true) meme s'il
    # a disparu de "recommendations" : sinon impossible de le re-inclure.
    items_by_id = {i["item_id"]: i for i in body["items"]}
    assert set(items_by_id) == {"111", "222"}
    assert items_by_id["222"]["excluded"] is True
    assert items_by_id["111"]["excluded"] is False
