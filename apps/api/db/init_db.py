"""Cree le schema en base. Pas de migrations versionnees en V1 (Alembic
viendra durcir ca plus tard) : usage=self-host qui demarre a vide.

Usage : python -m db.init_db
"""

import asyncio

from db.models import Base
from db.session import engine


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_db())
