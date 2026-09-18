"""Change le tier d'un utilisateur. Outil operateur uniquement : il n'existe
volontairement aucune route publique pour se passer premium soi-meme tant
qu'aucune facturation n'est branchee.

Usage : python -m scripts.set_tier <steamid64> <free|premium>
"""

import asyncio
import sys

from db.models import User
from db.session import SessionLocal

VALID_TIERS = {"free", "premium"}


async def set_tier(steamid64: str, tier: str) -> None:
    if tier not in VALID_TIERS:
        raise SystemExit(f"tier invalide : {tier!r}, attendu {sorted(VALID_TIERS)}")

    async with SessionLocal() as db_session:
        user = await db_session.get(User, steamid64)
        if user is None:
            raise SystemExit(f"utilisateur introuvable : {steamid64}")
        user.tier = tier
        await db_session.commit()
        print(f"{steamid64} -> tier={tier}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m scripts.set_tier <steamid64> <free|premium>")
    asyncio.run(set_tier(sys.argv[1], sys.argv[2]))
