from pricing.base import PriceQuote, PriceSource

STEAM_MARKET_PRICEOVERVIEW_ENDPOINT = "https://steamcommunity.com/market/priceoverview/"
CS2_APP_ID = 730


class SteamMarketPriceSource(PriceSource):
    async def get_price(self, item_name: str) -> PriceQuote | None:
        raise NotImplementedError
