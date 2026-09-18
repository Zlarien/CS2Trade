import os
from collections.abc import AsyncIterator

import httpx
from fastapi import Cookie, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.session import SESSION_COOKIE_NAME, get_session_steamid64
from db.models import ExcludedItem
from db.session import get_db_session as _get_db_session
from pricing.base import PriceSource
from pricing.skinport import SkinportPriceSource
from pricing.steam_market import SteamMarketPriceSource

get_db_session = _get_db_session

_redis_client: Redis | None = None


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


def get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    return _redis_client


async def get_current_steamid64(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    redis_client: Redis = Depends(get_redis_client),
) -> str:
    if session_id is None:
        raise HTTPException(status_code=401, detail="non authentifie")
    steamid64 = await get_session_steamid64(session_id, redis_client)
    if steamid64 is None:
        raise HTTPException(status_code=401, detail="session invalide ou expiree")
    return steamid64


async def get_excluded_item_ids(
    steamid64: str = Depends(get_current_steamid64),
    db_session: AsyncSession = Depends(get_db_session),
) -> set[str]:
    result = await db_session.execute(
        select(ExcludedItem.asset_id).where(ExcludedItem.user_steamid64 == steamid64)
    )
    return set(result.scalars().all())
