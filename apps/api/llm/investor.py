"""IA investisseur, tier premium uniquement.

Ne recalcule jamais un prix ni une probabilite : lit en lecture seule les
recommandations deja produites par engine.recommend (deterministe) et les
synthetise en langage naturel. engine/ n'importe jamais ce module (verifie
par import-linter), pour que le tier gratuit n'ait jamais de dependance a
une cle LLM.
"""

import os
from dataclasses import dataclass

import anthropic

from engine.recommend import ItemRecommendation

DEFAULT_MODEL = "claude-opus-5"
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


@dataclass(frozen=True)
class InvestorAdvice:
    summary: str
    model: str


def _model() -> str:
    return os.environ.get("LLM_MODEL", DEFAULT_MODEL)


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


async def get_investor_advice(
    recommendations: list[ItemRecommendation],
    question: str | None = None,
    client: anthropic.AsyncAnthropic | None = None,
) -> InvestorAdvice:
    active_client = client or anthropic.AsyncAnthropic()
    model = _model()

    data_block = _format_recommendations(recommendations)
    user_message = (
        f"Recommandations calculees pour cet inventaire :\n{data_block}\n\n"
        f"{question or 'Resume la strategie prioritaire pour ce mois-ci.'}"
    )

    try:
        response = await active_client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIError as exc:
        raise InvestorAdviceUnavailable(str(exc)) from exc

    text = next((block.text for block in response.content if block.type == "text"), "")
    return InvestorAdvice(summary=text, model=model)
