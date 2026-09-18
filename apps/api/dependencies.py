import os
from collections.abc import AsyncIterator

import httpx
from fastapi import Depends, HTTPException

from pricing.base import PriceSource
from pricing.skinport import SkinportPriceSource
from pricing.steam_market import SteamMarketPriceSource


async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        yield client


def get_steam_api_key() -> str:
    key = os.environ.get("STEAM_API_KEY")
    if not key:
        raise HTTPException(
            status_code=500,
            detail="STEAM_API_KEY manquant sur le serveur, voir .env.example",
        )
    return key


def get_price_sources(
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> list[PriceSource]:
    return [
        SkinportPriceSource(http_client=http_client),
        SteamMarketPriceSource(http_client=http_client),
    ]
