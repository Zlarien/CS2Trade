from functools import lru_cache
from pathlib import Path

import yaml

RULES_FILE = Path(__file__).parent / "rules.yaml"


@lru_cache(maxsize=1)
def load_rules() -> dict:
    return yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))


def rarities_ascending() -> list[str]:
    return load_rules()["rarities_ascending"]


def next_rarity(rarity: str) -> str | None:
    tiers = rarities_ascending()
    try:
        index = tiers.index(rarity)
    except ValueError:
        return None
    if index + 1 >= len(tiers):
        return None
    return tiers[index + 1]


def tradeable_weapon_categories() -> list[str]:
    return load_rules()["tradeable_weapon_categories"]


def marketplace_fee_rate() -> float:
    return load_rules()["trade_up"]["marketplace_fee_rate"]


def input_count() -> int:
    return load_rules()["trade_up"]["input_count"]


def wear_ranges() -> dict[str, tuple[float, float]]:
    return {name: tuple(bounds) for name, bounds in load_rules()["wear_ranges"].items()}


def classify_wear(float_value: float) -> str:
    for name, (low, high) in wear_ranges().items():
        if low <= float_value <= high:
            return name
    raise ValueError(f"float {float_value} hors des plages d'usure connues")
