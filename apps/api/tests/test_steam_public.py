import httpx
import pytest

from steam.public import (
    PrivateInventoryError,
    ProfileNotFoundError,
    SteamApiKeyRequired,
    SteamProfileError,
    extract_identifier,
    fetch_inventory,
    parse_inventory,
    resolve_steam_id64,
)


def _client_with_handler(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("76561198034202275", "76561198034202275"),
        ("https://steamcommunity.com/profiles/76561198034202275", "76561198034202275"),
        ("https://steamcommunity.com/profiles/76561198034202275/", "76561198034202275"),
        ("https://steamcommunity.com/id/gabelogannewell", "gabelogannewell"),
        ("gabelogannewell", "gabelogannewell"),
    ],
)
def test_extract_identifier(raw: str, expected: str) -> None:
    assert extract_identifier(raw) == expected


@pytest.mark.asyncio
async def test_resolve_steam_id64_passthrough_for_numeric_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP call expected for a raw SteamID64")

    steamid = await resolve_steam_id64(
        "76561198034202275", _client_with_handler(handler), steam_api_key="key"
    )
    assert steamid == "76561198034202275"


@pytest.mark.asyncio
async def test_resolve_steam_id64_passthrough_works_without_api_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP call expected for a raw SteamID64")

    steamid = await resolve_steam_id64(
        "76561198034202275", _client_with_handler(handler), steam_api_key=None
    )
    assert steamid == "76561198034202275"


@pytest.mark.asyncio
async def test_resolve_steam_id64_vanity_name_without_key_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP call expected when the key is missing")

    with pytest.raises(SteamApiKeyRequired):
        await resolve_steam_id64(
            "gabelogannewell", _client_with_handler(handler), steam_api_key=None
        )


@pytest.mark.asyncio
async def test_resolve_steam_id64_calls_vanity_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["vanityurl"] == "gabelogannewell"
        return httpx.Response(
            200, json={"response": {"success": 1, "steamid": "76561197960287930"}}
        )

    steamid = await resolve_steam_id64(
        "gabelogannewell", _client_with_handler(handler), steam_api_key="key"
    )
    assert steamid == "76561197960287930"


@pytest.mark.asyncio
async def test_resolve_steam_id64_raises_when_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": {"success": 42}})

    with pytest.raises(ProfileNotFoundError):
        await resolve_steam_id64("nope", _client_with_handler(handler), steam_api_key="key")


@pytest.mark.asyncio
async def test_fetch_inventory_raises_on_private_profile() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403)

    with pytest.raises(PrivateInventoryError):
        await fetch_inventory("76561198034202275", _client_with_handler(handler))


@pytest.mark.asyncio
async def test_fetch_inventory_raises_clean_error_on_rate_limit() -> None:
    # Reproduit un vrai 429 recu de Steam en test manuel (18/09/2026) : ne
    # doit jamais laisser fuiter un httpx.HTTPStatusError brut (500 opaque).
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    with pytest.raises(SteamProfileError, match="429|limite"):
        await fetch_inventory("76561198034202275", _client_with_handler(handler))


@pytest.mark.asyncio
async def test_fetch_inventory_wraps_other_http_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with pytest.raises(SteamProfileError, match="500"):
        await fetch_inventory("76561198034202275", _client_with_handler(handler))


@pytest.mark.asyncio
async def test_fetch_inventory_follows_pagination() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if "start_assetid" not in request.url.params:
            return httpx.Response(
                200,
                json={
                    "success": 1,
                    "assets": [{"assetid": "1", "classid": "c1", "instanceid": "0", "amount": "1"}],
                    "descriptions": [],
                    "more_items": 1,
                    "last_assetid": "1",
                },
            )
        return httpx.Response(
            200,
            json={
                "success": 1,
                "assets": [{"assetid": "2", "classid": "c2", "instanceid": "0", "amount": "1"}],
                "descriptions": [],
                "more_items": 0,
            },
        )

    assets, _ = await fetch_inventory("76561198034202275", _client_with_handler(handler))
    assert len(calls) == 2
    assert [a["assetid"] for a in assets] == ["1", "2"]


def test_parse_inventory_extracts_stattrak_and_wear() -> None:
    assets = [{"assetid": "111", "classid": "c1", "instanceid": "0", "amount": "1"}]
    descriptions = [
        {
            "classid": "c1",
            "instanceid": "0",
            "market_hash_name": "StatTrak™ AK-47 | Redline (Field-Tested)",
            "tradable": 1,
            "marketable": 1,
        }
    ]

    items = parse_inventory(assets, descriptions)

    assert len(items) == 1
    item = items[0]
    assert item.asset_id == "111"
    assert item.base_name == "AK-47 | Redline"
    assert item.wear == "Field-Tested"
    assert item.stattrak is True
    assert item.souvenir is False
    assert item.tradable is True


def test_parse_inventory_extracts_souvenir() -> None:
    assets = [{"assetid": "222", "classid": "c2", "instanceid": "0", "amount": "1"}]
    descriptions = [
        {
            "classid": "c2",
            "instanceid": "0",
            "market_hash_name": "Souvenir AWP | Asiimov (Field-Tested)",
            "tradable": 1,
            "marketable": 1,
        }
    ]

    items = parse_inventory(assets, descriptions)

    assert len(items) == 1
    item = items[0]
    assert item.base_name == "AWP | Asiimov"
    assert item.souvenir is True
    assert item.stattrak is False


def test_parse_inventory_skips_items_without_wear_suffix() -> None:
    assets = [{"assetid": "111", "classid": "c1", "instanceid": "0", "amount": "1"}]
    descriptions = [
        {
            "classid": "c1",
            "instanceid": "0",
            "market_hash_name": "Sticker | Katowice 2014",
            "tradable": 1,
            "marketable": 1,
        }
    ]

    assert parse_inventory(assets, descriptions) == []


def test_parse_inventory_skips_assets_without_matching_description() -> None:
    assets = [{"assetid": "111", "classid": "unknown", "instanceid": "0", "amount": "1"}]
    assert parse_inventory(assets, []) == []
