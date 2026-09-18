import asyncio
import re
import time

import httpx

from pricing.base import PriceQuote, PriceSource
from pricing.cache import AsyncCache, get_json, set_json

PRICEOVERVIEW_ENDPOINT = "https://steamcommunity.com/market/priceoverview/"
CS2_APP_ID = 730
CURRENCY_EUR = 3
QUOTE_TTL_SECONDS = 300
MIN_REQUEST_INTERVAL_SECONDS = 6.0

_PRICE_RE = re.compile(r"[\d.,]+")


def parse_eur_price(raw: str) -> float:
    """Parse un prix Steam au format europeen, ex: '1.234,56€' ou '31,83€'."""
    match = _PRICE_RE.search(raw)
    if match is None:
        raise ValueError(f"no numeric price found in {raw!r}")
    digits = match.group(0)
    if "," in digits:
        digits = digits.replace(".", "").replace(",", ".")
    return float(digits)


class SteamMarketPriceSource(PriceSource):
    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        cache: AsyncCache | None = None,
        ttl_seconds: int = QUOTE_TTL_SECONDS,
        min_request_interval_seconds: float = MIN_REQUEST_INTERVAL_SECONDS,
    ) -> None:
        self._http_client = http_client or httpx.AsyncClient()
        self._owns_client = http_client is None
        self._cache = cache
        self._ttl_seconds = ttl_seconds
        self._min_interval = min_request_interval_seconds
        self._last_request_at: float | None = None
        self._request_lock = asyncio.Lock()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http_client.aclose()

    async def get_price(self, item_name: str) -> PriceQuote | None:
        cache_key = f"steam_market:{item_name}"
        cached = await get_json(self._cache, cache_key)
        if cached is not None:
            return PriceQuote(**cached, source="steam_market")

        await self._respect_rate_limit()

        response = await self._http_client.get(
            PRICEOVERVIEW_ENDPOINT,
            params={
                "appid": CS2_APP_ID,
                "currency": CURRENCY_EUR,
                "market_hash_name": item_name,
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            # Steam renvoie souvent une erreur HTTP (pas un JSON propre) pour
            # un item sans historique de ventes, en plus des vraies pannes :
            # traite comme "pas de prix ici", jamais comme un crash.
            return None
        payload = response.json()

        if not payload.get("success") or "median_price" not in payload:
            return None

        quote_data = {
            "item_name": item_name,
            "price": parse_eur_price(payload["median_price"]),
            "currency": "EUR",
            "volume": int(payload["volume"].replace(",", "")) if payload.get("volume") else None,
        }
        await set_json(self._cache, cache_key, quote_data, self._ttl_seconds)
        return PriceQuote(**quote_data, source="steam_market")

    async def _respect_rate_limit(self) -> None:
        async with self._request_lock:
            if self._last_request_at is not None:
                elapsed = time.monotonic() - self._last_request_at
                wait_for = self._min_interval - elapsed
                if wait_for > 0:
                    await asyncio.sleep(wait_for)
            self._last_request_at = time.monotonic()
