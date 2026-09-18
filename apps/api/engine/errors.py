class EngineError(Exception):
    pass


class UnknownSkin(EngineError):
    pass


class TradeUpNotEligible(EngineError):
    pass


class PricingUnavailable(EngineError):
    def __init__(self, missing_market_hash_names: list[str]) -> None:
        self.missing_market_hash_names = missing_market_hash_names
        super().__init__(
            "prix indisponible pour : " + ", ".join(missing_market_hash_names)
        )
