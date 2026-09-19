import pytest

from engine.recommend import Action, ItemRecommendation
from llm.investor import InvestorAdviceUnavailable, LLMProviderError, get_investor_advice


class _FakeProvider:
    def __init__(self, response_text: str | None = None, error: Exception | None = None) -> None:
        self._response_text = response_text
        self._error = error
        self.last_call: dict | None = None

    async def complete(self, *, system: str, user_message: str, model: str) -> str:
        self.last_call = {"system": system, "user_message": user_message, "model": model}
        if self._error is not None:
            raise self._error
        return self._response_text


SAMPLE_RECOMMENDATIONS = [
    ItemRecommendation(
        item_id="1", action=Action.SELL, reason="valeur marche 15.00 EUR", price=15.0
    ),
    ItemRecommendation(
        item_id="2", action=Action.TRADE_UP, reason="trade-up vers Restricted", price=3.2
    ),
]


@pytest.mark.asyncio
async def test_get_investor_advice_returns_text_from_response() -> None:
    fake_provider = _FakeProvider(response_text="Priorise l'item 2 pour le trade-up.")

    advice = await get_investor_advice(SAMPLE_RECOMMENDATIONS, None, client=fake_provider)

    assert advice.summary == "Priorise l'item 2 pour le trade-up."
    assert advice.model


@pytest.mark.asyncio
async def test_get_investor_advice_includes_data_and_question_in_prompt() -> None:
    fake_provider = _FakeProvider(response_text="ok")

    await get_investor_advice(SAMPLE_RECOMMENDATIONS, "Dois-je vendre maintenant ?", fake_provider)

    sent_message = fake_provider.last_call["user_message"]
    assert "item 1" in sent_message
    assert "trade-up vers Restricted" in sent_message
    assert "Dois-je vendre maintenant ?" in sent_message


@pytest.mark.asyncio
async def test_get_investor_advice_handles_empty_recommendations() -> None:
    fake_provider = _FakeProvider(response_text="Rien a recommander.")

    advice = await get_investor_advice([], None, client=fake_provider)

    assert advice.summary == "Rien a recommander."


@pytest.mark.asyncio
async def test_get_investor_advice_wraps_api_error() -> None:
    fake_provider = _FakeProvider(error=LLMProviderError("connexion impossible"))

    with pytest.raises(InvestorAdviceUnavailable):
        await get_investor_advice(SAMPLE_RECOMMENDATIONS, None, client=fake_provider)
