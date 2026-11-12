from decimal import Decimal

from sqlalchemy import CheckConstraint, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

COLORS = ("RED", "YELLOW", "LIGHT_GREEN", "GREEN")  # worst → best


class ColorZone(Base):
    """Where a colour starts for one index. A zone runs from its min_value
    up to the next colour's min_value."""

    __tablename__ = "index_color_zones"
    __table_args__ = (
        UniqueConstraint("index_name", "color"),
        CheckConstraint("index_name IN ('NDVI','SAVI','MSAVI','NDMI','NDRE','RECI')", name="index_valid"),
        CheckConstraint("color IN ('RED','YELLOW','LIGHT_GREEN','GREEN')", name="color_valid"),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    index_name: Mapped[str] = mapped_column(String(5))
    color: Mapped[str] = mapped_column(String(11))
    min_value: Mapped[Decimal] = mapped_column(Numeric(5, 3))  # RECI can go above 1
