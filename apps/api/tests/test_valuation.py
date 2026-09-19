import pytest

from engine.valuation import build_market_hash_name, value_item, value_market_hash_name
from pricing.base import PriceQuote, PriceSource


class FakePriceSource(PriceSource):
    def __init__(self, prices: dict[str, PriceQuote]) -> None:
        self._prices = prices

    async def get_price(self, item_name: str) -> PriceQuote | None:
        return self._prices.get(item_name)


def test_build_market_hash_name_normal() -> None:
    assert (
        build_market_hash_name("AK-47 | Redline", "Field-Tested")
        == "AK-47 | Redline (Field-Tested)"
    )


def test_build_market_hash_name_stattrak() -> None:
    name = build_market_hash_name("AK-47 | Redline", "Field-Tested", stattrak=True)
    assert name == "StatTrak™ AK-47 | Redline (Field-Tested)"


def test_build_market_hash_name_rejects_stattrak_and_souvenir() -> None:
    with pytest.raises(ValueError, match="StatTrak"):
        build_market_hash_name("AK-47 | Redline", "Field-Tested", stattrak=True, souvenir=True)


@pytest.mark.asyncio
async def test_value_item_falls_back_to_second_source() -> None:
    name = "AK-47 | Redline (Field-Tested)"
    primary = FakePriceSource({})
    secondary = FakePriceSource(
        {name: PriceQuote(item_name=name, price=12.5, currency="EUR", source="fallback")}
    )

    result = await value_item("AK-47 | Redline", "Field-Tested", [primary, secondary])

    assert result is not None
    assert result.price == 12.5
    assert result.source == "fallback"


@pytest.mark.asyncio
async def test_value_item_returns_none_when_no_source_has_price() -> None:
    result = await value_item("AK-47 | Redline", "Field-Tested", [FakePriceSource({})])
    assert result is None


@pytest.mark.asyncio
async def test_value_market_hash_name_prices_a_name_directly() -> None:
    name = "Fracture Case"
    quote = PriceQuote(item_name=name, price=0.30, currency="EUR", source="skinport")
    source = FakePriceSource({name: quote})

    result = await value_market_hash_name(name, [source])

    assert result is not None
    assert result.market_hash_name == name
    assert result.price == 0.30
