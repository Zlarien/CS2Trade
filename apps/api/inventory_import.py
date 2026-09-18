from engine.float_estimate import estimate_float_from_wear
from engine.recommend import InventoryItem
from refdata.loader import get_skin
from steam.public import ParsedInventoryItem


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
