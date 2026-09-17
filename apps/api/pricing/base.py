from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PriceQuote:
    item_name: str
    price: float
    currency: str
    source: str
    volume: int | None = None


class PriceSource(ABC):
    @abstractmethod
    async def get_price(self, item_name: str) -> PriceQuote | None: ...
