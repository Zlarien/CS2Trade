import pytest

from auth.session import create_session, destroy_session, get_session_steamid64


class FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)


@pytest.mark.asyncio
async def test_create_and_read_session() -> None:
    store = FakeRedis()
    session_id = await create_session("76561198034202275", store)

    steamid64 = await get_session_steamid64(session_id, store)
    assert steamid64 == "76561198034202275"


@pytest.mark.asyncio
async def test_unknown_session_returns_none() -> None:
    store = FakeRedis()
    assert await get_session_steamid64("nope", store) is None


@pytest.mark.asyncio
async def test_destroy_session_invalidates_it() -> None:
    store = FakeRedis()
    session_id = await create_session("76561198034202275", store)

    await destroy_session(session_id, store)

    assert await get_session_steamid64(session_id, store) is None
