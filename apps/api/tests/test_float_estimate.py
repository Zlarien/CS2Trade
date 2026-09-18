import pytest

from engine.float_estimate import estimate_float_from_wear
from refdata.loader import get_skin


def test_estimate_float_midpoint_within_range() -> None:
    skin = get_skin("MAG-7 | Heaven Guard")  # min_float=0, max_float=0.4
    assert skin is not None
    # Field-Tested range [0.15, 0.38] clipped to [0, 0.4] -> midpoint 0.265
    estimate = estimate_float_from_wear(skin, "Field-Tested")
    assert estimate == 0.265


def test_estimate_float_clipped_to_skin_range() -> None:
    skin = get_skin("USP-S | Guardian")  # min_float=0, max_float=0.38
    assert skin is not None
    # Battle-Scarred [0.45, 1.0] ne recoupe pas [0, 0.38] -> repli sur le skin entier
    estimate = estimate_float_from_wear(skin, "Battle-Scarred")
    assert estimate == 0.19


def test_estimate_float_unknown_wear_raises() -> None:
    skin = get_skin("MAG-7 | Heaven Guard")
    assert skin is not None
    with pytest.raises(ValueError, match="usure inconnue"):
        estimate_float_from_wear(skin, "Not A Wear")
