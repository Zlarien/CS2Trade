from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import InventorySnapshot
from dependencies import get_current_steamid64, get_db_session

router = APIRouter(prefix="/me/portfolio-history", tags=["portfolio"])


@router.get("")
async def get_portfolio_history(
    steamid64: str = Depends(get_current_steamid64),
    db_session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    """Alimente par scripts/daily_sync.py (pas de sync automatique en V1)."""
    result = await db_session.execute(
        select(InventorySnapshot)
        .where(InventorySnapshot.user_steamid64 == steamid64)
        .order_by(InventorySnapshot.captured_at)
    )
    snapshots = result.scalars().all()
    return [
        {
            "captured_at": s.captured_at.isoformat(),
            "total_value": s.total_value,
            "currency": s.currency,
            "item_count": s.item_count,
        }
        for s in snapshots
    ]
