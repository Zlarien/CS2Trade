import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

SNAPSHOT_DIR = Path(__file__).parent / "snapshot"
SKINS_FILE = SNAPSHOT_DIR / "skins.json"


@dataclass(frozen=True)
class SkinRef:
    name: str
    weapon_category: str
    rarity: str
    collection: str | None
    min_float: float
    max_float: float
    stattrak_capable: bool
    souvenir_capable: bool
    wears: tuple[str, ...]


def _to_skin_ref(raw: dict) -> SkinRef:
    collections = raw.get("collections") or []
    return SkinRef(
        name=raw["name"],
        weapon_category=raw["category"]["name"],
        rarity=raw["rarity"]["name"],
        collection=collections[0]["name"] if collections else None,
        min_float=raw["min_float"],
        max_float=raw["max_float"],
        stattrak_capable=raw.get("stattrak", False),
        souvenir_capable=raw.get("souvenir", False),
        wears=tuple(w["name"] for w in raw.get("wears") or []),
    )


@lru_cache(maxsize=1)
def load_skins() -> tuple[SkinRef, ...]:
    raw_skins = json.loads(SKINS_FILE.read_text(encoding="utf-8"))
    # Quelques familles Doppler/Gamma Doppler partagent un nom d'affichage entre
    # plusieurs phases (paint_index distincts). On garde une seule entree
    # representative par nom : limitation connue, pas un bug de parsing.
    by_name: dict[str, SkinRef] = {}
    for raw in raw_skins:
        by_name[raw["name"]] = _to_skin_ref(raw)
    return tuple(by_name.values())


@lru_cache(maxsize=1)
def _skins_by_name() -> dict[str, SkinRef]:
    return {skin.name: skin for skin in load_skins()}


def get_skin(name: str) -> SkinRef | None:
    return _skins_by_name().get(name)


def skins_by_collection_and_rarity(collection: str, rarity: str) -> list[SkinRef]:
    return [s for s in load_skins() if s.collection == collection and s.rarity == rarity]
