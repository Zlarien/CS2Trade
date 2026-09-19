"""IA investisseur, tier premium uniquement.

Ne recalcule jamais un prix ni une probabilite : lit en lecture seule les
recommandations deja produites par engine.recommend (deterministe) et les
synthetise en langage naturel. engine/ n'importe jamais ce module (verifie
par import-linter), pour que le tier gratuit n'ait jamais de dependance a
une cle LLM.

Le fournisseur (Anthropic ou Groq) se choisit via LLM_PROVIDER, pour
pouvoir tourner sur une cle gratuite (Groq) sans toucher au reste du code.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from engine.recommend import ItemRecommendation

DEFAULT_MODEL_BY_PROVIDER = {
    "anthropic": "claude-opus-5",
    "groq": "openai/gpt-oss-120b",
}
MAX_TOKENS = 2048

SYSTEM_PROMPT = (
    "Tu es un conseiller strategique pour un inventaire de skins CS2 "
    "(Counter-Strike 2). Les recommandations garder/vendre/trade-up et "
    "leurs valeurs t'arrivent deja calculees par un moteur deterministe : "
    "tu ne recalcules jamais un prix ni une probabilite, tu n'inventes "
    "aucun chiffre absent des donnees fournies. Ton role est d'expliquer "
    "ces recommandations en langage naturel et de proposer une "
    "priorisation. Reponds en francais, de facon courte et actionnable."
)


class InvestorAdviceUnavailable(Exception):
    pass


class LLMProviderError(Exception):
    """Erreur remontee par un LLMProvider, quel que soit le SDK derriere."""


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, *, system: str, user_message: str, model: str) -> str: ...


class AnthropicProvider(LLMProvider):
    def __init__(self, client=None) -> None:
        import anthropic

        self._client = client or anthropic.AsyncAnthropic()

    async def complete(self, *, system: str, user_message: str, model: str) -> str:
        import anthropic

        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
        except anthropic.APIError as exc:
            raise LLMProviderError(str(exc)) from exc
        return next((block.text for block in response.content if block.type == "text"), "")


class GroqProvider(LLMProvider):
    def __init__(self, client=None) -> None:
        import groq

        self._client = client or groq.AsyncGroq()

    async def complete(self, *, system: str, user_message: str, model: str) -> str:
        import groq

        try:
            response = await self._client.chat.completions.create(
                model=model,
                max_tokens=MAX_TOKENS,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_message},
                ],
            )
        except groq.APIError as exc:
            raise LLMProviderError(str(exc)) from exc
        return response.choices[0].message.content or ""


def provider_name() -> str:
    return os.environ.get("LLM_PROVIDER", "anthropic")


def _model() -> str:
    name = provider_name()
    return os.environ.get("LLM_MODEL") or DEFAULT_MODEL_BY_PROVIDER.get(
        name, DEFAULT_MODEL_BY_PROVIDER["anthropic"]
    )


def default_provider() -> LLMProvider:
    return GroqProvider() if provider_name() == "groq" else AnthropicProvider()


def _format_recommendations(recommendations: list[ItemRecommendation]) -> str:
    if not recommendations:
        return "(inventaire vide ou entierement exclu)"
    lines = []
    for rec in recommendations:
        value = f"{rec.price:.2f}" if rec.price is not None else "inconnue"
        lines.append(
            f"- item {rec.item_id} : {rec.action.value}, raison={rec.reason}, valeur/EV={value}"
        )
    return "\n".join(lines)


@dataclass(frozen=True)
class InvestorAdvice:
    summary: str
    model: str


async def get_investor_advice(
    recommendations: list[ItemRecommendation],
    question: str | None = None,
    client: LLMProvider | None = None,
) -> InvestorAdvice:
    provider = client or default_provider()
    model = _model()

    data_block = _format_recommendations(recommendations)
    user_message = (
        f"Recommandations calculees pour cet inventaire :\n{data_block}\n\n"
        f"{question or 'Resume la strategie prioritaire pour ce mois-ci.'}"
    )

    try:
        text = await provider.complete(system=SYSTEM_PROMPT, user_message=user_message, model=model)
    except LLMProviderError as exc:
        raise InvestorAdviceUnavailable(str(exc)) from exc

    return InvestorAdvice(summary=text, model=model)
