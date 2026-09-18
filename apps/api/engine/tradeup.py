from collections import Counter
from dataclasses import dataclass

from engine import rules
from engine.errors import PricingUnavailable, TradeUpNotEligible, UnknownSkin
from engine.valuation import build_market_hash_name, value_item
from pricing.base import PriceSource
from refdata.loader import SkinRef, get_skin, skins_by_collection_and_rarity


@dataclass(frozen=True)
class OwnedItem:
    base_name: str
    float_value: float
    stattrak: bool = False


@dataclass(frozen=True)
class TradeUpOutcome:
    collection: str
    skin_name: str
    wear: str
    probability: float
    price: float


@dataclass(frozen=True)
class TradeUpResult:
    inputs: tuple[OwnedItem, ...]
    target_rarity: str
    outcomes: tuple[TradeUpOutcome, ...]
    gross_expected_value: float
    fees: float
    opportunity_cost: float
    net_expected_value: float


def _normalize_float(float_value: float, skin: SkinRef) -> float:
    return (float_value - skin.min_float) / (skin.max_float - skin.min_float)


def _remap_float(normalized: float, skin: SkinRef) -> float:
    return normalized * (skin.max_float - skin.min_float) + skin.min_float


def _resolve_inputs(inputs: list[OwnedItem]) -> list[SkinRef]:
    skins = []
    for item in inputs:
        skin = get_skin(item.base_name)
        if skin is None:
            raise UnknownSkin(item.base_name)
        if skin.weapon_category not in rules.tradeable_weapon_categories():
            raise TradeUpNotEligible(
                f"{item.base_name} ({skin.weapon_category}) n'est pas eligible au trade-up"
            )
        skins.append(skin)
    return skins


def _validate_same_category(inputs: list[OwnedItem]) -> bool:
    stattrak_flags = {item.stattrak for item in inputs}
    if len(stattrak_flags) > 1:
        raise TradeUpNotEligible("les 10 items doivent etre tous normaux ou tous StatTrak")
    return stattrak_flags.pop()


def _validate_same_rarity(skins: list[SkinRef]) -> str:
    rarities = {skin.rarity for skin in skins}
    if len(rarities) > 1:
        raise TradeUpNotEligible(f"les 10 items n'ont pas la meme rarete : {sorted(rarities)}")
    return rarities.pop()


async def compute_trade_up(
    inputs: list[OwnedItem], price_sources: list[PriceSource], fee_rate: float | None = None
) -> TradeUpResult:
    expected_count = rules.input_count()
    if len(inputs) != expected_count:
        raise TradeUpNotEligible(f"un trade-up contract prend exactement {expected_count} items")

    skins = _resolve_inputs(inputs)
    stattrak = _validate_same_category(inputs)
    input_rarity = _validate_same_rarity(skins)

    target_rarity = rules.next_rarity(input_rarity)
    if target_rarity is None:
        raise TradeUpNotEligible(f"{input_rarity} est deja le palier maximum, pas de trade-up")

    collection_counts = Counter(skin.collection for skin in skins)
    if None in collection_counts:
        raise TradeUpNotEligible("un item sans collection ne peut pas etre trade up")

    eligible_by_collection: dict[str, list[SkinRef]] = {}
    for collection in collection_counts:
        candidates = [
            s
            for s in skins_by_collection_and_rarity(collection, target_rarity)
            if not stattrak or s.stattrak_capable
        ]
        if not candidates:
            raise TradeUpNotEligible(
                f"la collection {collection} n'a pas de skin {target_rarity} eligible"
            )
        eligible_by_collection[collection] = candidates

    normalized_floats = [
        _normalize_float(item.float_value, skin) for item, skin in zip(inputs, skins, strict=True)
    ]
    avg_normalized = sum(normalized_floats) / len(normalized_floats)

    missing: list[str] = []
    outcomes: list[TradeUpOutcome] = []
    gross_expected_value = 0.0

    for collection, count in collection_counts.items():
        candidates = eligible_by_collection[collection]
        p_collection = count / expected_count
        p_skin = p_collection / len(candidates)

        for skin in candidates:
            output_float = _remap_float(avg_normalized, skin)
            wear = rules.classify_wear(output_float)
            valuation = await value_item(skin.name, wear, price_sources, stattrak=stattrak)
            if valuation is None:
                missing.append(build_market_hash_name(skin.name, wear, stattrak=stattrak))
                continue
            outcomes.append(
                TradeUpOutcome(
                    collection=collection,
                    skin_name=skin.name,
                    wear=wear,
                    probability=p_skin,
                    price=valuation.price,
                )
            )
            gross_expected_value += p_skin * valuation.price

    opportunity_cost = 0.0
    for item, skin in zip(inputs, skins, strict=True):
        wear = rules.classify_wear(item.float_value)
        valuation = await value_item(item.base_name, wear, price_sources, stattrak=item.stattrak)
        if valuation is None:
            missing.append(build_market_hash_name(item.base_name, wear, stattrak=item.stattrak))
            continue
        opportunity_cost += valuation.price

    if missing:
        raise PricingUnavailable(missing)

    effective_fee_rate = rules.marketplace_fee_rate() if fee_rate is None else fee_rate
    fees = gross_expected_value * effective_fee_rate
    net_expected_value = gross_expected_value - fees - opportunity_cost

    return TradeUpResult(
        inputs=tuple(inputs),
        target_rarity=target_rarity,
        outcomes=tuple(outcomes),
        gross_expected_value=gross_expected_value,
        fees=fees,
        opportunity_cost=opportunity_cost,
        net_expected_value=net_expected_value,
    )
