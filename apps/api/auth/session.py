import secrets
from typing import Protocol

SESSION_COOKIE_NAME = "cs2trade_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 jours
_SESSION_KEY_PREFIX = "session:"


class AsyncKeyValueStore(Protocol):
    async def get(self, key: str) -> bytes | str | None: ...
    async def set(self, key: str, value: str, ex: int) -> object: ...
    async def delete(self, key: str) -> object: ...


def _session_key(session_id: str) -> str:
    return f"{_SESSION_KEY_PREFIX}{session_id}"


async def create_session(steamid64: str, store: AsyncKeyValueStore) -> str:
    session_id = secrets.token_urlsafe(32)
    await store.set(_session_key(session_id), steamid64, ex=SESSION_TTL_SECONDS)
    return session_id


async def get_session_steamid64(session_id: str, store: AsyncKeyValueStore) -> str | None:
    value = await store.get(_session_key(session_id))
    if value is None:
        return None
    return value.decode() if isinstance(value, bytes) else value


async def destroy_session(session_id: str, store: AsyncKeyValueStore) -> None:
    await store.delete(_session_key(session_id))
