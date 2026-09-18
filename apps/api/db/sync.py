import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import InventorySnapshot
from engine import rules
from engine.valuation import value_item
from inventory_import import build_inventory_items
from pricing.base import PriceSource
from steam.public import fetch_inventory, parse_inventory


async def sync_user_portfolio(
    steamid64: str,
    db_session: AsyncSession,
    http_client: httpx.AsyncClient,
    price_sources: list[PriceSource],
) -> InventorySnapshot:
    """Recalcule la valeur totale du portefeuille et l'ajoute a l'historique.

    A appeler depuis scripts/daily_sync.py (cron cote self-hoster), pas
    depuis une requete HTTP : peut etre lent sur un gros inventaire.
    """
    assets, descriptions = await fetch_inventory(steamid64, http_client)
    parsed = parse_inventory(assets, descriptions)
    items, _ = build_inventory_items(parsed)

    total_value = 0.0
    priced_count = 0
    for item in items:
        wear = rules.classify_wear(item.float_value)
        valuation = await value_item(item.base_name, wear, price_sources, stattrak=item.stattrak)
        if valuation is not None:
            total_value += valuation.price
            priced_count += 1

    snapshot = InventorySnapshot(
        user_steamid64=steamid64,
        total_value=total_value,
        currency="EUR",
        item_count=priced_count,
    )
    db_session.add(snapshot)
    await db_session.commit()
    return snapshot
