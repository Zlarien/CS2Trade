from dataclasses import dataclass


@dataclass(frozen=True)
class ItemValuation:
    item_id: str
    market_price: float
    currency: str
    source: str


def value_item(item_id: str) -> ItemValuation:
    raise NotImplementedError
