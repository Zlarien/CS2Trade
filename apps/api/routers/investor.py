import anthropic
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db.models import User
from dependencies import (
    get_anthropic_client,
    get_excluded_item_ids,
    get_http_client,
    get_price_sources,
    require_premium_tier,
)
from inventory_import import get_recommendations_for_user
from llm.investor import InvestorAdviceUnavailable, get_investor_advice
from pricing.base import PriceSource
from steam.public import PrivateInventoryError, SteamProfileError

router = APIRouter(prefix="/me/investor-advice", tags=["investor"])


class InvestorAdviceRequest(BaseModel):
    question: str | None = None


@router.post("")
async def post_investor_advice(
    body: InvestorAdviceRequest,
    user: User = Depends(require_premium_tier),
    excluded_item_ids: set[str] = Depends(get_excluded_item_ids),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    price_sources: list[PriceSource] = Depends(get_price_sources),
    llm_client: anthropic.AsyncAnthropic = Depends(get_anthropic_client),
) -> dict:
    try:
        _, _, _, recommendations = await get_recommendations_for_user(
            user.steamid64, excluded_item_ids, http_client, price_sources
        )
    except PrivateInventoryError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SteamProfileError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        advice = await get_investor_advice(recommendations, body.question, client=llm_client)
    except InvestorAdviceUnavailable as exc:
        raise HTTPException(
            status_code=502, detail=f"IA investisseur indisponible : {exc}"
        ) from exc

    return {"summary": advice.summary, "model": advice.model}
