import json
from typing import Any, Protocol


class AsyncCache(Protocol):
    async def get(self, key: str) -> bytes | str | None: ...
    async def set(self, key: str, value: str, ex: int) -> Any: ...


async def get_json(cache: AsyncCache | None, key: str) -> Any | None:
    if cache is None:
        return None
    raw = await cache.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def set_json(cache: AsyncCache | None, key: str, value: Any, ttl_seconds: int) -> None:
    if cache is None:
        return
    await cache.set(key, json.dumps(value), ex=ttl_seconds)
