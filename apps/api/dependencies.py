import os
from collections.abc import AsyncIterator

import anthropic
import httpx
from fastapi import Cookie, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.session import SESSION_COOKIE_NAME, get_session_steamid64
from db.models import ExcludedItem, User
from db.session import get_db_session as _get_db_session
from pricing.base import PriceSource
from pricing.skinport import SkinportPriceSource
from pricing.steam_market import SteamMarketPriceSource

get_db_session = _get_db_session

_redis_client: Redis | None = None


async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        yield client


def get_steam_api_key() -> str | None:
    """None si absent : un SteamID64 brut ou une URL /profiles/<id> n'en ont
    pas besoin (voir steam.public.resolve_steam_id64). Seule la resolution
    d'un vanity name l'exige, et leve alors une erreur specifique."""
    return os.environ.get("STEAM_API_KEY") or None


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


async def get_current_user(
    steamid64: str = Depends(get_current_steamid64),
    db_session: AsyncSession = Depends(get_db_session),
) -> User:
    user = await db_session.get(User, steamid64)
    if user is None:
        raise HTTPException(status_code=404, detail="utilisateur introuvable")
    return user


async def require_premium_tier(user: User = Depends(get_current_user)) -> User:
    """Gating pour les fonctionnalites premium (ex: llm/ investisseur).

    Aucune facturation branchee en V1 : le tier se change en base
    (voir scripts/set_tier.py), jamais via une route publique.
    """
    if user.tier != "premium":
        raise HTTPException(
            status_code=403,
            detail=f"fonctionnalite premium, ton tier actuel est '{user.tier}'",
        )
    return user


def get_anthropic_client() -> anthropic.AsyncAnthropic:
    """Cle resolue depuis l'environnement (ANTHROPIC_API_KEY), jamais en dur.

    Surchargee en test pour ne jamais faire de vrai appel reseau.
    """
    return anthropic.AsyncAnthropic()
