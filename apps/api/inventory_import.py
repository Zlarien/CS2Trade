import httpx

from engine.float_estimate import estimate_float_from_wear
from engine.recommend import InventoryItem, ItemRecommendation, recommend_for_inventory
from pricing.base import PriceSource
from refdata.loader import get_skin
from steam.public import ParsedInventoryItem, fetch_inventory, parse_inventory


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
            )
        )
    return items, skipped_unknown


async def get_recommendations_for_user(
    steamid64: str,
    excluded_item_ids: set[str],
    http_client: httpx.AsyncClient,
    price_sources: list[PriceSource],
) -> tuple[list[ParsedInventoryItem], list[InventoryItem], int, list[ItemRecommendation]]:
    """Composition partagee par routers/inventory.py et routers/investor.py."""
    assets, descriptions = await fetch_inventory(steamid64, http_client)
    parsed = parse_inventory(assets, descriptions)
    items, skipped_unknown = build_inventory_items(parsed)
    recommendations = await recommend_for_inventory(items, excluded_item_ids, price_sources)
    return parsed, items, skipped_unknown, recommendations
