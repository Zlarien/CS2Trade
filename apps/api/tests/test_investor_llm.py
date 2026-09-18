from dataclasses import dataclass

import anthropic
import httpx2
import pytest

from engine.recommend import Action, ItemRecommendation
from llm.investor import InvestorAdviceUnavailable, get_investor_advice


@dataclass
class _FakeTextBlock:
    text: str
    type: str = "text"


class _FakeMessages:
    def __init__(self, response_text: str | None = None, error: Exception | None = None) -> None:
        self._response_text = response_text
        self._error = error
        self.last_kwargs: dict | None = None

    async def create(self, **kwargs):
        self.last_kwargs = kwargs
        if self._error is not None:
            raise self._error
        return type("FakeResponse", (), {"content": [_FakeTextBlock(self._response_text)]})()


class _FakeAnthropicClient:
    def __init__(self, response_text: str | None = None, error: Exception | None = None) -> None:
        self.messages = _FakeMessages(response_text, error)


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
    fake_client = _FakeAnthropicClient(response_text="Priorise l'item 2 pour le trade-up.")

    advice = await get_investor_advice(SAMPLE_RECOMMENDATIONS, None, client=fake_client)

    assert advice.summary == "Priorise l'item 2 pour le trade-up."
    assert advice.model


@pytest.mark.asyncio
async def test_get_investor_advice_includes_data_and_question_in_prompt() -> None:
    fake_client = _FakeAnthropicClient(response_text="ok")

    await get_investor_advice(SAMPLE_RECOMMENDATIONS, "Dois-je vendre maintenant ?", fake_client)

    sent_message = fake_client.messages.last_kwargs["messages"][0]["content"]
    assert "item 1" in sent_message
    assert "trade-up vers Restricted" in sent_message
    assert "Dois-je vendre maintenant ?" in sent_message


@pytest.mark.asyncio
async def test_get_investor_advice_handles_empty_recommendations() -> None:
    fake_client = _FakeAnthropicClient(response_text="Rien a recommander.")

    advice = await get_investor_advice([], None, client=fake_client)

    assert advice.summary == "Rien a recommander."


@pytest.mark.asyncio
async def test_get_investor_advice_wraps_api_error() -> None:
    connection_error = anthropic.APIConnectionError(
        request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    )
    fake_client = _FakeAnthropicClient(error=connection_error)

    with pytest.raises(InvestorAdviceUnavailable):
        await get_investor_advice(SAMPLE_RECOMMENDATIONS, None, client=fake_client)
