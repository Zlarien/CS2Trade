import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from dependencies import (
    get_current_steamid64,
    get_excluded_item_ids,
    get_http_client,
    get_price_sources,
    get_steam_api_key,
)
from engine.recommend import recommend_for_inventory
from inventory_import import build_inventory_items
from pricing.base import PriceSource
from steam.public import (
    PrivateInventoryError,
    ProfileNotFoundError,
    SteamProfileError,
    extract_identifier,
    fetch_inventory,
    parse_inventory,
    resolve_steam_id64,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


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
        "item_count": len(items),
        "skipped_unknown_items": skipped_unknown,
        "float_is_estimated": True,
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
        assets, descriptions = await fetch_inventory(steamid64, http_client)
    except PrivateInventoryError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SteamProfileError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    parsed = parse_inventory(assets, descriptions)
    items, skipped_unknown = build_inventory_items(parsed)

    recommendations = await recommend_for_inventory(
        items, excluded_item_ids=excluded_item_ids, price_sources=price_sources
    )

    return {
        "steamid64": steamid64,
        "item_count": len(items),
        "excluded_count": len(excluded_item_ids),
        "skipped_unknown_items": skipped_unknown,
        "float_is_estimated": True,
        "recommendations": recommendations,
    }
