from dataclasses import dataclass


@dataclass(frozen=True)
class TradeUpOutcome:
    collection: str
    skin: str
    wear: str
    probability: float
    price: float


@dataclass(frozen=True)
class TradeUpResult:
    inputs: list[str]
    outcomes: list[TradeUpOutcome]
    expected_value: float
    opportunity_cost: float
    fees: float
    net_ev: float


def compute_trade_up(input_item_ids: list[str]) -> TradeUpResult:
    raise NotImplementedError
