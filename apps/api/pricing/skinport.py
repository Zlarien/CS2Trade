from pricing.base import PriceQuote, PriceSource

SKINPORT_ITEMS_ENDPOINT = "https://api.skinport.com/v1/items"


class SkinportPriceSource(PriceSource):
    async def get_price(self, item_name: str) -> PriceQuote | None:
        raise NotImplementedError
