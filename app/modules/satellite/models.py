from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, IdMixin


class IndexSnapshot(IdMixin, CreatedAtMixin, Base):
    """One index value of one farm on one satellite date (the farm's history)."""

    __tablename__ = "farm_index_snapshots"
    __table_args__ = (
        UniqueConstraint("farm_id", "observed_on", "index_name"),  # makes the upsert possible
        Index("ix_snapshots_farm_date", "farm_id", "observed_on"),
    )

    farm_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("farms.id", ondelete="CASCADE"))
    observed_on: Mapped[date] = mapped_column(Date)       # the SATELLITE date, not today
    index_name: Mapped[str] = mapped_column(String(5))
    value: Mapped[Decimal] = mapped_column(Numeric(5, 3))
    dominant_color: Mapped[str | None] = mapped_column(String(11))
    red_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    yellow_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    light_green_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    green_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
