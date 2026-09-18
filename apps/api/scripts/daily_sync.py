"""A brancher sur un cron du self-hoster (docker-compose n'en lance aucun
par defaut). Recalcule la valeur du portefeuille de chaque utilisateur lie.

Usage : python -m scripts.daily_sync
"""

import asyncio

import httpx
from sqlalchemy import select

from db.models import User
from db.session import SessionLocal
from db.sync import sync_user_portfolio
from pricing.skinport import SkinportPriceSource
from pricing.steam_market import SteamMarketPriceSource


async def main() -> None:
    async with SessionLocal() as db_session, httpx.AsyncClient() as http_client:
        price_sources = [
            SkinportPriceSource(http_client=http_client),
            SteamMarketPriceSource(http_client=http_client),
        ]

        result = await db_session.execute(select(User.steamid64))
        for steamid64 in result.scalars().all():
            try:
                snapshot = await sync_user_portfolio(
                    steamid64, db_session, http_client, price_sources
                )
            except Exception as exc:  # on continue avec les autres utilisateurs
                print(f"{steamid64}: echec sync ({exc})")
                continue
            print(
                f"{steamid64}: {snapshot.total_value:.2f} {snapshot.currency} "
                f"({snapshot.item_count} items values)"
            )


if __name__ == "__main__":
    asyncio.run(main())
