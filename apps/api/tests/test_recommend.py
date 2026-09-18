import pytest

from engine.recommend import Action, InventoryItem, recommend_for_inventory
from pricing.base import PriceQuote, PriceSource


class FakePriceSource(PriceSource):
    def __init__(self, prices: dict[str, float]) -> None:
        self._prices = prices

    async def get_price(self, item_name: str) -> PriceQuote | None:
        price = self._prices.get(item_name)
        if price is None:
            return None
        return PriceQuote(item_name=item_name, price=price, currency="EUR", source="fake")


def _mag7_items(count: int = 10) -> list[InventoryItem]:
    return [
        InventoryItem(item_id=f"mag7-{i}", base_name="MAG-7 | Heaven Guard", float_value=0.2)
        for i in range(count)
    ]


PROFITABLE_PRICES = {
    "MAG-7 | Heaven Guard (Field-Tested)": 0.5,
    "FAMAS | Sergeant (Battle-Scarred)": 20.0,
    "MAC-10 | Heat (Battle-Scarred)": 20.0,
    "SG 553 | Pulse (Field-Tested)": 20.0,
    "USP-S | Guardian (Field-Tested)": 20.0,
    "AK-47 | Redline (Field-Tested)": 15.0,
    "Souvenir AK-47 | Redline (Field-Tested)": 40.0,
}


@pytest.mark.asyncio
async def test_full_group_recommends_trade_up() -> None:
    items = _mag7_items(10)
    recommendations = await recommend_for_inventory(
        items, excluded_item_ids=set(), price_sources=[FakePriceSource(PROFITABLE_PRICES)]
    )

    assert len(recommendations) == 10
    assert all(r.action == Action.TRADE_UP for r in recommendations)
    assert all(r.trade_up_group == tuple(f"mag7-{i}" for i in range(10)) for r in recommendations)


@pytest.mark.asyncio
async def test_item_without_group_is_sold() -> None:
    items = [InventoryItem(item_id="ak-1", base_name="AK-47 | Redline", float_value=0.2)]
    recommendations = await recommend_for_inventory(
        items, excluded_item_ids=set(), price_sources=[FakePriceSource(PROFITABLE_PRICES)]
    )

    assert len(recommendations) == 1
    assert recommendations[0].action == Action.SELL
    assert recommendations[0].price == pytest.approx(15.0)


@pytest.mark.asyncio
async def test_excluded_item_is_never_recommended() -> None:
    items = _mag7_items(9) + [
        InventoryItem(item_id="excluded-1", base_name="Nova | Antique", float_value=0.1)
    ]
    recommendations = await recommend_for_inventory(
        items,
        excluded_item_ids={"excluded-1"},
        price_sources=[FakePriceSource(PROFITABLE_PRICES)],
    )

    assert all(r.item_id != "excluded-1" for r in recommendations)


@pytest.mark.asyncio
async def test_item_with_no_price_is_held() -> None:
    items = [InventoryItem(item_id="unpriced-1", base_name="AK-47 | Redline", float_value=0.2)]
    recommendations = await recommend_for_inventory(
        items, excluded_item_ids=set(), price_sources=[FakePriceSource({})]
    )

    assert len(recommendations) == 1
    assert recommendations[0].action == Action.HOLD


@pytest.mark.asyncio
async def test_souvenir_item_is_never_grouped_for_trade_up() -> None:
    # 9 items normaux + 1 Souvenir de meme skin/rarete : ne doit jamais
    # completer un lot de trade-up (mecanique non implementee, on ne
    # risque pas une EV fausse). Le Souvenir doit rester seul, SELL.
    items = _mag7_items(9) + [
        InventoryItem(
            item_id="souvenir-1",
            base_name="MAG-7 | Heaven Guard",
            float_value=0.2,
            souvenir=True,
        )
    ]
    recommendations = await recommend_for_inventory(
        items, excluded_item_ids=set(), price_sources=[FakePriceSource(PROFITABLE_PRICES)]
    )

    by_id = {r.item_id: r for r in recommendations}
    assert all(by_id[f"mag7-{i}"].action != Action.TRADE_UP for i in range(9))
    assert by_id["souvenir-1"].action == Action.HOLD  # pas de prix Souvenir MAG-7 dans les fixtures


@pytest.mark.asyncio
async def test_souvenir_item_is_priced_with_souvenir_market_hash_name() -> None:
    items = [
        InventoryItem(
            item_id="souvenir-ak",
            base_name="AK-47 | Redline",
            float_value=0.2,
            souvenir=True,
        )
    ]
    recommendations = await recommend_for_inventory(
        items, excluded_item_ids=set(), price_sources=[FakePriceSource(PROFITABLE_PRICES)]
    )

    assert recommendations[0].action == Action.SELL
    # prix Souvenir (40.0), pas le prix normal (15.0)
    assert recommendations[0].price == pytest.approx(40.0)
