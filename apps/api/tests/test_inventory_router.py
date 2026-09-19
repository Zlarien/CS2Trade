import httpx
import pytest
from fastapi.testclient import TestClient

import dependencies
from dependencies import get_http_client, get_steam_api_key
from main import app

STEAMID64 = "76561198034202275"

INVENTORY_RESPONSE = {
    "success": 1,
    "assets": [
        {"assetid": "111", "classid": "c1", "instanceid": "0", "amount": "1"},
        {"assetid": "222", "classid": "c2", "instanceid": "0", "amount": "1"},
        {"assetid": "333", "classid": "c3", "instanceid": "0", "amount": "1"},
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
            "market_hash_name": "Sticker | Katowice 2014",
            "tradable": 1,
            "marketable": 1,
        },
        {
            "classid": "c3",
            "instanceid": "0",
            "market_hash_name": "Not A Real Skin | Nope (Field-Tested)",
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
        "market_hash_name": "Sticker | Katowice 2014",
        "currency": "EUR",
        "median_price": 120.0,
        "quantity": 3,
    },
]


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.host == "steamcommunity.com" and "/inventory/" in request.url.path:
        return httpx.Response(200, json=INVENTORY_RESPONSE)
    if request.url.host == "api.skinport.com":
        return httpx.Response(200, json=SKINPORT_RESPONSE)
    raise AssertionError(f"unexpected request to {request.url}")


@pytest.fixture
def client(fake_redis) -> TestClient:
    async def override_http_client():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as c:
            yield c

    app.dependency_overrides[get_http_client] = override_http_client
    app.dependency_overrides[get_steam_api_key] = lambda: "dummy-key"
    app.dependency_overrides[dependencies.get_redis_client] = lambda: fake_redis
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_get_recommendations_end_to_end(client: TestClient) -> None:
    response = client.get("/inventory/recommendations", params={"identifier": STEAMID64})

    assert response.status_code == 200
    body = response.json()
    assert body["steamid64"] == STEAMID64
    # Le sticker n'a pas d'usure : c'est un item divers (parse_misc_items),
    # jamais un skin inconnu. Le skin fictif, lui, a une usure mais est
    # absent du referentiel : seul celui-la compte comme "unknown".
    assert body["item_count"] == 2
    assert body["skipped_unknown_items"] == 1
    recommendations_by_id = {r["item_id"]: r for r in body["recommendations"]}
    assert len(recommendations_by_id) == 2
    assert recommendations_by_id["111"]["action"] == "sell"
    assert recommendations_by_id["111"]["price"] == pytest.approx(3.5)
    assert recommendations_by_id["222"]["action"] == "sell"
    assert recommendations_by_id["222"]["price"] == pytest.approx(120.0)


def test_numeric_steamid64_works_without_any_steam_api_key(
    client: TestClient,
) -> None:
    # Le fixture "client" force deja dummy-key, on la retire explicitement :
    # un SteamID64 brut ne doit jamais exiger de cle.
    app.dependency_overrides[get_steam_api_key] = lambda: None

    response = client.get("/inventory/recommendations", params={"identifier": STEAMID64})

    assert response.status_code == 200
    assert response.json()["steamid64"] == STEAMID64


def test_vanity_name_without_key_returns_helpful_400(client: TestClient) -> None:
    app.dependency_overrides[get_steam_api_key] = lambda: None

    response = client.get("/inventory/recommendations", params={"identifier": "somevanityname"})

    assert response.status_code == 400
    assert "STEAM_API_KEY" in response.json()["detail"]
