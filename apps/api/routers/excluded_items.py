from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ExcludedItem
from dependencies import get_current_steamid64, get_db_session

router = APIRouter(prefix="/me/excluded-items", tags=["excluded-items"])


class ExcludeItemRequest(BaseModel):
    asset_id: str
    reason: str | None = None


class ExcludedItemResponse(BaseModel):
    asset_id: str
    reason: str | None


@router.get("", response_model=list[ExcludedItemResponse])
async def list_excluded_items(
    steamid64: str = Depends(get_current_steamid64),
    db_session: AsyncSession = Depends(get_db_session),
) -> list[ExcludedItem]:
    result = await db_session.execute(
        select(ExcludedItem).where(ExcludedItem.user_steamid64 == steamid64)
    )
    return list(result.scalars().all())


@router.post("", response_model=ExcludedItemResponse, status_code=status.HTTP_201_CREATED)
async def add_excluded_item(
    body: ExcludeItemRequest,
    steamid64: str = Depends(get_current_steamid64),
    db_session: AsyncSession = Depends(get_db_session),
) -> ExcludedItem:
    existing = await db_session.get(ExcludedItem, (steamid64, body.asset_id))
    if existing is not None:
        return existing

    item = ExcludedItem(user_steamid64=steamid64, asset_id=body.asset_id, reason=body.reason)
    db_session.add(item)
    await db_session.commit()
    return item


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_excluded_item(
    asset_id: str,
    steamid64: str = Depends(get_current_steamid64),
    db_session: AsyncSession = Depends(get_db_session),
) -> Response:
    await db_session.execute(
        delete(ExcludedItem).where(
            ExcludedItem.user_steamid64 == steamid64, ExcludedItem.asset_id == asset_id
        )
    )
    await db_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
