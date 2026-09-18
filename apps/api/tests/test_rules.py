from engine import rules


def test_rarities_ascending_order() -> None:
    assert rules.rarities_ascending() == [
        "Consumer Grade",
        "Industrial Grade",
        "Mil-Spec Grade",
        "Restricted",
        "Classified",
        "Covert",
    ]


def test_next_rarity_progresses_one_tier() -> None:
    assert rules.next_rarity("Mil-Spec Grade") == "Restricted"
    assert rules.next_rarity("Restricted") == "Classified"


def test_next_rarity_none_at_top_tier() -> None:
    assert rules.next_rarity("Covert") is None


def test_next_rarity_none_for_unknown_rarity() -> None:
    assert rules.next_rarity("Contraband") is None


def test_classify_wear_boundaries() -> None:
    assert rules.classify_wear(0.0) == "Factory New"
    assert rules.classify_wear(0.2) == "Field-Tested"
    assert rules.classify_wear(0.5) == "Battle-Scarred"
    assert rules.classify_wear(1.0) == "Battle-Scarred"
