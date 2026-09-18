import pytest

from engine.errors import PricingUnavailable, TradeUpNotEligible, UnknownSkin
from engine.tradeup import OwnedItem, compute_trade_up
from pricing.base import PriceQuote, PriceSource

# Cas verifie a la main sur The Phoenix Collection (refdata/snapshot/skins.json) :
# 10x MAG-7 | Heaven Guard (Mil-Spec, min_float=0, max_float=0.4) a float=0.2
# -> normalise = 0.5 pour chacun, moyenne = 0.5
# -> palier suivant = Restricted, 4 skins eligibles dans la collection, p=1/4 chacun
# -> float de sortie = 0.5 * (max-min) + min par skin :
#      FAMAS | Sergeant   (0.1-1.0)  -> 0.55 -> Battle-Scarred
#      MAC-10 | Heat      (0.0-1.0)  -> 0.50 -> Battle-Scarred
#      SG 553 | Pulse     (0.1-0.6)  -> 0.35 -> Field-Tested
#      USP-S | Guardian   (0.0-0.38) -> 0.19 -> Field-Tested
PHOENIX_MIL_SPEC_INPUT = "MAG-7 | Heaven Guard"
PHOENIX_RESTRICTED_PRICES = {
    "FAMAS | Sergeant (Battle-Scarred)": 5.0,
    "MAC-10 | Heat (Battle-Scarred)": 6.0,
    "SG 553 | Pulse (Field-Tested)": 8.0,
    "USP-S | Guardian (Field-Tested)": 10.0,
}
INPUT_PRICE = 2.0
INPUT_MARKET_HASH_NAME = "MAG-7 | Heaven Guard (Field-Tested)"


class FakePriceSource(PriceSource):
    def __init__(self, prices: dict[str, float]) -> None:
        self._prices = prices

    async def get_price(self, item_name: str) -> PriceQuote | None:
        price = self._prices.get(item_name)
        if price is None:
            return None
        return PriceQuote(item_name=item_name, price=price, currency="EUR", source="fake")


def _ten_mag7_inputs(float_value: float = 0.2) -> list[OwnedItem]:
    return [OwnedItem(PHOENIX_MIL_SPEC_INPUT, float_value) for _ in range(10)]


def _full_price_source() -> FakePriceSource:
    prices = dict(PHOENIX_RESTRICTED_PRICES)
    prices[INPUT_MARKET_HASH_NAME] = INPUT_PRICE
    return FakePriceSource(prices)


@pytest.mark.asyncio
async def test_trade_up_matches_hand_computed_ev() -> None:
    result = await compute_trade_up(_ten_mag7_inputs(), [_full_price_source()])

    assert result.target_rarity == "Restricted"
    assert len(result.outcomes) == 4
    for outcome in result.outcomes:
        assert outcome.probability == pytest.approx(0.25)

    wears = {o.skin_name: o.wear for o in result.outcomes}
    assert wears == {
        "FAMAS | Sergeant": "Battle-Scarred",
        "MAC-10 | Heat": "Battle-Scarred",
        "SG 553 | Pulse": "Field-Tested",
        "USP-S | Guardian": "Field-Tested",
    }

    assert result.gross_expected_value == pytest.approx(7.25)
    assert result.opportunity_cost == pytest.approx(20.0)
    assert result.fees == pytest.approx(7.25 * 0.12)
    assert result.net_expected_value == pytest.approx(7.25 - 7.25 * 0.12 - 20.0)


@pytest.mark.asyncio
async def test_trade_up_custom_fee_rate() -> None:
    result = await compute_trade_up(_ten_mag7_inputs(), [_full_price_source()], fee_rate=0.0)
    assert result.fees == 0.0
    assert result.net_expected_value == pytest.approx(7.25 - 20.0)


@pytest.mark.asyncio
async def test_trade_up_rejects_wrong_item_count() -> None:
    with pytest.raises(TradeUpNotEligible, match="10 items"):
        await compute_trade_up(_ten_mag7_inputs()[:9], [_full_price_source()])


@pytest.mark.asyncio
async def test_trade_up_rejects_mixed_stattrak() -> None:
    inputs = _ten_mag7_inputs()
    inputs[0] = OwnedItem(PHOENIX_MIL_SPEC_INPUT, 0.2, stattrak=True)
    with pytest.raises(TradeUpNotEligible, match="StatTrak"):
        await compute_trade_up(inputs, [_full_price_source()])


@pytest.mark.asyncio
async def test_trade_up_rejects_mixed_rarity() -> None:
    inputs = _ten_mag7_inputs()
    inputs[0] = OwnedItem("AK-47 | Redline", 0.2)  # Classified, pas Mil-Spec
    with pytest.raises(TradeUpNotEligible, match="rarete"):
        await compute_trade_up(inputs, [_full_price_source()])


@pytest.mark.asyncio
async def test_trade_up_rejects_top_tier_input() -> None:
    inputs = [OwnedItem("AWP | Asiimov", 0.3) for _ in range(10)]  # Covert
    with pytest.raises(TradeUpNotEligible, match="maximum"):
        await compute_trade_up(inputs, [_full_price_source()])


@pytest.mark.asyncio
async def test_trade_up_rejects_unknown_skin() -> None:
    inputs = _ten_mag7_inputs()
    inputs[0] = OwnedItem("Not A Real Skin | Nope", 0.2)
    with pytest.raises(UnknownSkin):
        await compute_trade_up(inputs, [_full_price_source()])


@pytest.mark.asyncio
async def test_trade_up_raises_when_price_missing() -> None:
    incomplete_prices = dict(PHOENIX_RESTRICTED_PRICES)
    del incomplete_prices["USP-S | Guardian (Field-Tested)"]
    incomplete_prices[INPUT_MARKET_HASH_NAME] = INPUT_PRICE

    with pytest.raises(PricingUnavailable) as exc_info:
        await compute_trade_up(_ten_mag7_inputs(), [FakePriceSource(incomplete_prices)])

    assert "USP-S | Guardian (Field-Tested)" in exc_info.value.missing_market_hash_names
