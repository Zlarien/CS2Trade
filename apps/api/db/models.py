from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    steamid64: Mapped[str] = mapped_column(String(17), primary_key=True)
    tier: Mapped[str] = mapped_column(String(20), default="free", server_default="free")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ExcludedItem(Base):
    """Items que le moteur ne doit jamais recommander de vendre ou trade up.

    Filtrage applique dans engine.recommend avant tout calcul, jamais
    seulement masque cote UI.
    """

    __tablename__ = "excluded_items"

    user_steamid64: Mapped[str] = mapped_column(ForeignKey("users.steamid64"), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InventorySnapshot(Base):
    """Point d'historique de la valeur totale du portefeuille, un par sync."""

    __tablename__ = "inventory_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_steamid64: Mapped[str] = mapped_column(ForeignKey("users.steamid64"))
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    total_value: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    item_count: Mapped[int] = mapped_column(Integer)
