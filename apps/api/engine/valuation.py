from dataclasses import dataclass

from pricing.base import PriceSource


@dataclass(frozen=True)
class ItemValuation:
    market_hash_name: str
    price: float
    currency: str
    source: str


def build_market_hash_name(
    base_name: str, wear: str, stattrak: bool = False, souvenir: bool = False
) -> str:
    if stattrak and souvenir:
        raise ValueError("un skin ne peut pas etre a la fois StatTrak et Souvenir")
    prefix = "StatTrak™ " if stattrak else "Souvenir " if souvenir else ""
    return f"{prefix}{base_name} ({wear})"


async def value_market_hash_name(
    market_hash_name: str, price_sources: list[PriceSource]
) -> ItemValuation | None:
    for source in price_sources:
        quote = await source.get_price(market_hash_name)
        if quote is not None:
            return ItemValuation(
                market_hash_name=market_hash_name,
                price=quote.price,
                currency=quote.currency,
                source=quote.source,
            )
    return None


async def value_item(
    base_name: str,
    wear: str,
    price_sources: list[PriceSource],
    stattrak: bool = False,
    souvenir: bool = False,
) -> ItemValuation | None:
    market_hash_name = build_market_hash_name(base_name, wear, stattrak, souvenir)
    return await value_market_hash_name(market_hash_name, price_sources)
