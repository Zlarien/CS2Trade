"""Estime un float quand seule l'usure (wear bucket) est connue.

Steam n'expose jamais le float exact via son inventaire public (il faut un
inspect link + connexion au Game Coordinator, hors scope V1). Utilise pour
l'import manuel niveau 1 (SteamID public). Le resultat est une approximation
et doit toujours etre signale comme telle a l'utilisateur.
"""

from engine import rules
from refdata.loader import SkinRef


def estimate_float_from_wear(skin: SkinRef, wear: str) -> float:
    ranges = rules.wear_ranges()
    if wear not in ranges:
        raise ValueError(f"usure inconnue : {wear!r}")

    low, high = ranges[wear]
    clipped_low = max(low, skin.min_float)
    clipped_high = min(high, skin.max_float)
    if clipped_low > clipped_high:
        clipped_low, clipped_high = skin.min_float, skin.max_float
    return (clipped_low + clipped_high) / 2
