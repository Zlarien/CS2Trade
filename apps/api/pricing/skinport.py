import httpx

from pricing.base import PriceQuote, PriceSource
from pricing.cache import AsyncCache, get_json, set_json

ITEMS_ENDPOINT = "https://api.skinport.com/v1/items"
CS2_APP_ID = 730
CATALOG_CACHE_KEY = "skinport:catalog:v1"
CATALOG_TTL_SECONDS = 900


class SkinportPriceSource(PriceSource):
    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        cache: AsyncCache | None = None,
        ttl_seconds: int = CATALOG_TTL_SECONDS,
    ) -> None:
        self._http_client = http_client or httpx.AsyncClient()
        self._owns_client = http_client is None
        self._cache = cache
        self._ttl_seconds = ttl_seconds

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http_client.aclose()

    async def get_price(self, item_name: str) -> PriceQuote | None:
        catalog = await self._get_catalog()
        entry = catalog.get(item_name)
        if entry is None:
            return None
        return PriceQuote(
            item_name=item_name,
            price=entry["median_price"],
            currency=entry["currency"],
            source="skinport",
            volume=entry["quantity"],
        )

    async def _get_catalog(self) -> dict[str, dict]:
        cached = await get_json(self._cache, CATALOG_CACHE_KEY)
        if cached is not None:
            return cached

        response = await self._http_client.get(
            ITEMS_ENDPOINT, params={"app_id": CS2_APP_ID, "currency": "EUR"}
        )
        response.raise_for_status()
        items = response.json()

        catalog = {
            item["market_hash_name"]: {
                "median_price": item["median_price"],
                "currency": item["currency"],
                "quantity": item["quantity"],
            }
            for item in items
            if item.get("median_price") is not None
        }

        await set_json(self._cache, CATALOG_CACHE_KEY, catalog, self._ttl_seconds)
        return catalog
