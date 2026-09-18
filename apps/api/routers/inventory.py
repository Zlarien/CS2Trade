import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from dependencies import get_http_client, get_price_sources, get_steam_api_key
from engine.float_estimate import estimate_float_from_wear
from engine.recommend import InventoryItem, recommend_for_inventory
from pricing.base import PriceSource
from refdata.loader import get_skin
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

    items: list[InventoryItem] = []
    skipped_unknown = 0
    for entry in parsed:
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
