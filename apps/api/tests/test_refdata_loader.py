from refdata.loader import get_skin, load_skins, skins_by_collection_and_rarity


def test_load_skins_returns_a_large_set() -> None:
    skins = load_skins()
    assert len(skins) > 1000


def test_get_skin_known_item() -> None:
    skin = get_skin("MAG-7 | Heaven Guard")
    assert skin is not None
    assert skin.collection == "The Phoenix Collection"
    assert skin.rarity == "Mil-Spec Grade"
    assert skin.min_float == 0
    assert skin.max_float == 0.4


def test_get_skin_unknown_item() -> None:
    assert get_skin("Not A Real Skin | Nope") is None


def test_skins_by_collection_and_rarity_phoenix_restricted() -> None:
    skins = skins_by_collection_and_rarity("The Phoenix Collection", "Restricted")
    names = sorted(s.name for s in skins)
    assert names == [
        "FAMAS | Sergeant",
        "MAC-10 | Heat",
        "SG 553 | Pulse",
        "USP-S | Guardian",
    ]
