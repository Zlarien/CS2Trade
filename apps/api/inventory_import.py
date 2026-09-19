import httpx

from engine.float_estimate import estimate_float_from_wear
from engine.recommend import (
    InventoryItem,
    ItemRecommendation,
    MiscItem,
    recommend_for_inventory,
    recommend_for_misc_items,
)
from pricing.base import PriceSource
from refdata.loader import get_skin
from steam.public import (
    ParsedInventoryItem,
    ParsedMiscItem,
    fetch_inventory,
    parse_inventory,
    parse_misc_items,
)


def build_inventory_items(
    parsed_items: list[ParsedInventoryItem],
) -> tuple[list[InventoryItem], int]:
    items: list[InventoryItem] = []
    skipped_unknown = 0
    for entry in parsed_items:
        skin = get_skin(entry.base_name)
        if skin is None:
            skipped_unknown += 1
            continue
        estimated_float = estimate_float_from_wear(skin, entry.wear)
        items.append(
            InventoryItem(
                item_id=entry.asset_id,
                base_name=entry.base_name,
                float_value=estimated_float,
                stattrak=entry.stattrak,
                souvenir=entry.souvenir,
            )
        )
    return items, skipped_unknown


def build_misc_items(parsed_misc_items: list[ParsedMiscItem]) -> list[MiscItem]:
    return [
        MiscItem(item_id=entry.asset_id, market_hash_name=entry.market_hash_name)
        for entry in parsed_misc_items
    ]


async def get_full_inventory(
    steamid64: str,
    excluded_item_ids: set[str],
    http_client: httpx.AsyncClient,
    price_sources: list[PriceSource],
) -> tuple[
    list[ParsedInventoryItem],
    list[ParsedMiscItem],
    list[InventoryItem],
    int,
    list[ItemRecommendation],
]:
    """Composition partagee par routers/inventory.py et routers/investor.py.

    Couvre les skins (garder/vendre/trade-up) et les items sans usure
    (caisses, stickers, agents, patches, pins, music kits...), qui n'ont
    jamais de trade-up mais peuvent avoir une vraie valeur marche.
    """
    assets, descriptions = await fetch_inventory(steamid64, http_client)

    parsed = parse_inventory(assets, descriptions)
    items, skipped_unknown = build_inventory_items(parsed)
    skin_recommendations = await recommend_for_inventory(items, excluded_item_ids, price_sources)

    parsed_misc = parse_misc_items(assets, descriptions)
    misc_items = build_misc_items(parsed_misc)
    misc_recommendations = await recommend_for_misc_items(
        misc_items, excluded_item_ids, price_sources
    )

    return (
        parsed,
        parsed_misc,
        items,
        skipped_unknown,
        skin_recommendations + misc_recommendations,
    )
