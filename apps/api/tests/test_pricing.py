import httpx
import pytest

from pricing.skinport import ITEMS_ENDPOINT, SkinportPriceSource
from pricing.steam_market import PRICEOVERVIEW_ENDPOINT, SteamMarketPriceSource, parse_eur_price


class FakeCache:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:
        self._store[key] = value


def _client_with_handler(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_skinport_returns_price_for_known_item() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200,
            json=[
                {
                    "market_hash_name": "AK-47 | Redline (Field-Tested)",
                    "currency": "EUR",
                    "median_price": 32.01,
                    "quantity": 120,
                }
            ],
        )

    source = SkinportPriceSource(http_client=_client_with_handler(handler))
    quote = await source.get_price("AK-47 | Redline (Field-Tested)")

    assert quote is not None
    assert quote.price == 32.01
    assert quote.currency == "EUR"
    assert quote.source == "skinport"
    assert quote.volume == 120
    assert len(calls) == 1
    assert calls[0].url.path == httpx.URL(ITEMS_ENDPOINT).path


@pytest.mark.asyncio
async def test_skinport_returns_none_for_unknown_item() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    source = SkinportPriceSource(http_client=_client_with_handler(handler))
    quote = await source.get_price("Nonexistent Skin")

    assert quote is None


@pytest.mark.asyncio
async def test_skinport_uses_cache_on_second_call() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200,
            json=[
                {
                    "market_hash_name": "AK-47 | Redline (Field-Tested)",
                    "currency": "EUR",
                    "median_price": 32.01,
                    "quantity": 120,
                }
            ],
        )

    cache = FakeCache()
    source = SkinportPriceSource(http_client=_client_with_handler(handler), cache=cache)

    await source.get_price("AK-47 | Redline (Field-Tested)")
    await source.get_price("AK-47 | Redline (Field-Tested)")

    assert len(calls) == 1


@pytest.mark.asyncio
async def test_skinport_returns_none_on_http_error_instead_of_raising() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    source = SkinportPriceSource(http_client=_client_with_handler(handler))
    quote = await source.get_price("AK-47 | Redline (Field-Tested)")

    assert quote is None


@pytest.mark.asyncio
async def test_skinport_http_error_is_not_cached() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503)

    cache = FakeCache()
    source = SkinportPriceSource(http_client=_client_with_handler(handler), cache=cache)

    await source.get_price("AK-47 | Redline (Field-Tested)")
    await source.get_price("AK-47 | Redline (Field-Tested)")

    assert len(calls) == 2  # jamais de cache d'un echec, sinon 15min de "aucun prix"


def test_parse_eur_price_with_comma_decimal() -> None:
    assert parse_eur_price("31,83€") == 31.83


def test_parse_eur_price_with_thousands_separator() -> None:
    assert parse_eur_price("1.234,56€") == 1234.56


@pytest.mark.asyncio
async def test_steam_market_returns_price_for_known_item() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == httpx.URL(PRICEOVERVIEW_ENDPOINT).path
        return httpx.Response(
            200,
            json={
                "success": True,
                "lowest_price": "31,83€",
                "volume": "73",
                "median_price": "32,01€",
            },
        )

    source = SteamMarketPriceSource(
        http_client=_client_with_handler(handler), min_request_interval_seconds=0
    )
    quote = await source.get_price("AK-47 | Redline (Field-Tested)")

    assert quote is not None
    assert quote.price == 32.01
    assert quote.currency == "EUR"
    assert quote.source == "steam_market"
    assert quote.volume == 73


@pytest.mark.asyncio
async def test_steam_market_returns_none_on_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": False})

    source = SteamMarketPriceSource(
        http_client=_client_with_handler(handler), min_request_interval_seconds=0
    )
    quote = await source.get_price("Unknown Item")

    assert quote is None


@pytest.mark.asyncio
async def test_steam_market_returns_none_on_http_error_instead_of_raising() -> None:
    # Steam renvoie souvent une erreur HTTP (pas un JSON propre) pour un item
    # sans historique de ventes : ne doit jamais faire planter la requete.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    source = SteamMarketPriceSource(
        http_client=_client_with_handler(handler), min_request_interval_seconds=0
    )
    quote = await source.get_price("Item Sans Historique")

    assert quote is None


@pytest.mark.asyncio
async def test_steam_market_uses_cache_on_second_call() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "success": True,
                "lowest_price": "31,83€",
                "volume": "73",
                "median_price": "32,01€",
            },
        )

    cache = FakeCache()
    source = SteamMarketPriceSource(
        http_client=_client_with_handler(handler), cache=cache, min_request_interval_seconds=0
    )

    await source.get_price("AK-47 | Redline (Field-Tested)")
    await source.get_price("AK-47 | Redline (Field-Tested)")

    assert len(calls) == 1
