from dataclasses import dataclass
from pathlib import Path

SNAPSHOT_DIR = Path(__file__).parent / "snapshot"


@dataclass(frozen=True)
class SkinRef:
    name: str
    collection: str
    rarity: str
    min_float: float
    max_float: float
    stattrak_capable: bool


def load_skins() -> list[SkinRef]:
    raise NotImplementedError
