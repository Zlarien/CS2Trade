import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from dependencies import (
    get_current_steamid64,
    get_excluded_item_ids,
    get_http_client,
    get_price_sources,
    get_steam_api_key,
)
from engine.recommend import InventoryItem, recommend_for_inventory
from inventory_import import build_inventory_items, get_recommendations_for_user
from pricing.base import PriceSource
from steam.public import (
    ParsedInventoryItem,
    PrivateInventoryError,
    ProfileNotFoundError,
    SteamProfileError,
    extract_identifier,
    fetch_inventory,
    parse_inventory,
    resolve_steam_id64,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _serialize_items(
    parsed_items: list[ParsedInventoryItem],
    known_items: list[InventoryItem],
    excluded_item_ids: set[str],
) -> list[dict]:
    """Vue complete de l'inventaire, y compris les items exclus.

    Necessaire car engine.recommend filtre les items exclus AVANT tout
    calcul (jamais seulement masques cote UI) : ils n'apparaissent donc
    jamais dans "recommendations". Sans cette liste, l'UI n'aurait aucun
    moyen d'afficher un item exclu pour permettre de le re-inclure.
    """
    known_ids = {item.item_id for item in known_items}
    return [
        {
            "item_id": p.asset_id,
            "base_name": p.base_name,
            "wear": p.wear,
            "stattrak": p.stattrak,
            "souvenir": p.souvenir,
            "market_hash_name": p.market_hash_name,
            "excluded": p.asset_id in excluded_item_ids,
        }
        for p in parsed_items
        if p.asset_id in known_ids
    ]


@router.get("/recommendations")
async def get_recommendations(
    identifier: str = Query(
        ..., description="SteamID64, URL de profil Steam, ou vanity name"
    ),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    steam_api_key: str = Depends(get_steam_api_key),
    price_sources: list[PriceSource] = Depends(get_price_sources),
) -> dict:
    """Import ponctuel, sans compte lie : lecture de l'inventaire public uniquement."""
    try:
        raw_identifier = extract_identifier(identifier)
        steamid64 = await resolve_steam_id64(raw_identifier, http_client, steam_api_key)
        assets, descriptions = await fetch_inventory(steamid64, http_client)
    except PrivateInventoryError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SteamProfileError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    parsed = parse_inventory(assets, descriptions)
    items, skipped_unknown = build_inventory_items(parsed)

    recommendations = await recommend_for_inventory(
        items, excluded_item_ids=set(), price_sources=price_sources
    )

    return {
        "steamid64": steamid64,
        "authenticated": False,
        "item_count": len(items),
        "skipped_unknown_items": skipped_unknown,
        "float_is_estimated": True,
        "items": _serialize_items(parsed, items, set()),
        "recommendations": recommendations,
    }


@router.get("/me/recommendations")
async def get_my_recommendations(
    steamid64: str = Depends(get_current_steamid64),
    excluded_item_ids: set[str] = Depends(get_excluded_item_ids),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    price_sources: list[PriceSource] = Depends(get_price_sources),
) -> dict:
    """Compte Steam lie (OpenID) : applique les exclusions de l'utilisateur."""
    try:
        parsed, items, skipped_unknown, recommendations = await get_recommendations_for_user(
            steamid64, excluded_item_ids, http_client, price_sources
        )
    except PrivateInventoryError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SteamProfileError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "steamid64": steamid64,
        "authenticated": True,
        "item_count": len(items),
        "excluded_count": len(excluded_item_ids),
        "skipped_unknown_items": skipped_unknown,
        "float_is_estimated": True,
        "items": _serialize_items(parsed, items, excluded_item_ids),
        "recommendations": recommendations,
    }
