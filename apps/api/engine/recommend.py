from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from engine import rules
from engine.errors import PricingUnavailable, TradeUpNotEligible, UnknownSkin
from engine.tradeup import OwnedItem, compute_trade_up
from engine.valuation import value_item, value_market_hash_name
from pricing.base import PriceSource
from refdata.loader import get_skin


class Action(StrEnum):
    HOLD = "hold"
    SELL = "sell"
    TRADE_UP = "trade_up"


@dataclass(frozen=True)
class InventoryItem:
    item_id: str
    base_name: str
    float_value: float
    stattrak: bool = False
    souvenir: bool = False


@dataclass(frozen=True)
class ItemRecommendation:
    item_id: str
    action: Action
    reason: str
    price: float | None = None
    trade_up_group: tuple[str, ...] | None = None


def _group_key(item: InventoryItem) -> tuple[str, str, bool] | None:
    if item.souvenir:
        # Depuis le 22/05/2026, un Souvenir peut entrer dans un trade-up
        # contract (il perd ses attributs Souvenir, et compte une rarete
        # au-dessus des autres inputs). Regle non implementee : on ne
        # risque pas une EV fausse, un Souvenir n'est jamais groupe et
        # tombe dans le chemin individuel (valorisation correcte quand
        # meme, voir la construction du market_hash_name plus bas).
        return None
    skin = get_skin(item.base_name)
    if skin is None:
        return None
    if skin.weapon_category not in rules.tradeable_weapon_categories():
        return None
    return (skin.weapon_category, skin.rarity, item.stattrak)


async def recommend_for_inventory(
    items: list[InventoryItem],
    excluded_item_ids: set[str],
    price_sources: list[PriceSource],
) -> list[ItemRecommendation]:
    candidates = [item for item in items if item.item_id not in excluded_item_ids]

    groups: dict[tuple[str, str, bool], list[InventoryItem]] = defaultdict(list)
    ungrouped: list[InventoryItem] = []
    for item in candidates:
        key = _group_key(item)
        if key is None:
            ungrouped.append(item)
        else:
            groups[key].append(item)

    recommendations: dict[str, ItemRecommendation] = {}
    leftover: list[InventoryItem] = list(ungrouped)

    for group_items in groups.values():
        traded_ids: set[str] = set()

        while len(group_items) - len(traded_ids) >= rules.input_count():
            pool = [item for item in group_items if item.item_id not in traded_ids]
            pool.sort(key=lambda item: item.float_value)
            batch = pool[: rules.input_count()]

            owned = [OwnedItem(item.base_name, item.float_value, item.stattrak) for item in batch]
            try:
                result = await compute_trade_up(owned, price_sources)
            except (TradeUpNotEligible, UnknownSkin, PricingUnavailable):
                break

            per_item_ev = result.net_expected_value / rules.input_count()
            if per_item_ev <= 0:
                break

            group_ids = tuple(item.item_id for item in batch)
            for item in batch:
                recommendations[item.item_id] = ItemRecommendation(
                    item_id=item.item_id,
                    action=Action.TRADE_UP,
                    reason=(
                        f"trade-up vers {result.target_rarity}, "
                        f"EV nette par item ~{per_item_ev:.2f}"
                    ),
                    price=per_item_ev,
                    trade_up_group=group_ids,
                )
                traded_ids.add(item.item_id)

        leftover.extend(item for item in group_items if item.item_id not in traded_ids)

    for item in leftover:
        if item.item_id in recommendations:
            continue
        skin = get_skin(item.base_name)
        if skin is None:
            recommendations[item.item_id] = ItemRecommendation(
                item_id=item.item_id,
                action=Action.HOLD,
                reason="skin inconnu dans le referentiel",
            )
            continue

        wear = rules.classify_wear(item.float_value)
        valuation = await value_item(
            item.base_name, wear, price_sources, stattrak=item.stattrak, souvenir=item.souvenir
        )
        if valuation is None:
            recommendations[item.item_id] = ItemRecommendation(
                item_id=item.item_id,
                action=Action.HOLD,
                reason="prix indisponible sur les sources configurees",
            )
            continue

        recommendations[item.item_id] = ItemRecommendation(
            item_id=item.item_id,
            action=Action.SELL,
            reason=(
                f"pas de trade-up rentable identifie, "
                f"valeur marche {valuation.price:.2f} {valuation.currency}"
            ),
            price=valuation.price,
        )

    return [
        recommendations[item.item_id]
        for item in items
        if item.item_id not in excluded_item_ids
    ]


@dataclass(frozen=True)
class MiscItem:
    """Item sans usure (caisse, sticker, agent, patch, pin, music kit...).

    Jamais eligible au trade-up : juste garder ou vendre au prix marche.
    """

    item_id: str
    market_hash_name: str


async def recommend_for_misc_items(
    items: list[MiscItem],
    excluded_item_ids: set[str],
    price_sources: list[PriceSource],
) -> list[ItemRecommendation]:
    recommendations: list[ItemRecommendation] = []
    for item in items:
        if item.item_id in excluded_item_ids:
            continue
        valuation = await value_market_hash_name(item.market_hash_name, price_sources)
        if valuation is None:
            recommendations.append(
                ItemRecommendation(
                    item_id=item.item_id,
                    action=Action.HOLD,
                    reason="prix indisponible sur les sources configurees",
                )
            )
        else:
            recommendations.append(
                ItemRecommendation(
                    item_id=item.item_id,
                    action=Action.SELL,
                    reason=f"valeur marche {valuation.price:.2f} {valuation.currency}",
                    price=valuation.price,
                )
            )
    return recommendations
