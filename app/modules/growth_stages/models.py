from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

INDEX_NAMES = ("NDVI", "SAVI", "MSAVI", "NDMI", "NDRE", "RECI")


class GrowthStage(Base):
    """One stage of one crop, e.g. Wheat, 'Tillering', days 21-45 after sowing."""

    __tablename__ = "growth_stages"
    __table_args__ = (
        UniqueConstraint("crop_id", "day_from"),
        CheckConstraint("day_from >= 0 AND day_to >= day_from", name="days_valid"),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    crop_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("crop_types.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    day_from: Mapped[int] = mapped_column(SmallInteger)
    day_to: Mapped[int] = mapped_column(SmallInteger)

    ranges: Mapped[list["IndexRange"]] = relationship(
        cascade="all, delete-orphan",   # deleting a stage deletes its ranges
        lazy="selectin",                # always load ranges (async-safe)
        order_by="IndexRange.index_name",
    )


class IndexRange(Base):
    """The healthy value range of one satellite index during one stage."""

    __tablename__ = "growth_stage_index_ranges"
    __table_args__ = (
        UniqueConstraint("stage_id", "index_name"),
        CheckConstraint(f"index_name IN {INDEX_NAMES}", name="index_name_valid"),
        CheckConstraint("low <= high", name="low_le_high"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stage_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("growth_stages.id", ondelete="CASCADE"), index=True
    )
    index_name: Mapped[str] = mapped_column(String(5))
    low: Mapped[Decimal] = mapped_column(Numeric(4, 3))    # e.g. 0.350
    high: Mapped[Decimal] = mapped_column(Numeric(4, 3))   # e.g. 0.720
    title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
