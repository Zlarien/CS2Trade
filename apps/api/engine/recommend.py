from dataclasses import dataclass
from enum import StrEnum


class Action(StrEnum):
    HOLD = "hold"
    SELL = "sell"
    TRADE_UP = "trade_up"


@dataclass(frozen=True)
class ItemRecommendation:
    item_id: str
    action: Action
    reason: str


def recommend_for_inventory(
    item_ids: list[str], excluded_item_ids: set[str]
) -> list[ItemRecommendation]:
    raise NotImplementedError
