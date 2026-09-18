import pytest
from fastapi import HTTPException

from db.models import User
from dependencies import get_current_user, require_premium_tier


@pytest.mark.asyncio
async def test_get_current_user_raises_for_unknown_steamid(db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(steamid64="nope", db_session=session)
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_require_premium_tier_blocks_free_user(db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        session.add(User(steamid64="1", tier="free"))
        await session.commit()
        user = await session.get(User, "1")

    with pytest.raises(HTTPException) as exc_info:
        await require_premium_tier(user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_premium_tier_allows_premium_user(db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        session.add(User(steamid64="2", tier="premium"))
        await session.commit()
        user = await session.get(User, "2")

    result = await require_premium_tier(user)
    assert result.steamid64 == "2"
