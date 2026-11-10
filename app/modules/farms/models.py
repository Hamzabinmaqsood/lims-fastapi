from datetime import date
from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Date, ForeignKey, Index, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, IdMixin
from sqlalchemy import CheckConstraint 


class Farm(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "farms"
    __table_args__ = (
        # GiST = the special index type for shapes. Makes "farms in this area" fast.
        Index("ix_farms_boundary", "boundary", postgresql_using="gist"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
    )

    owner_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), default="farm")
    # SRID 4326 = normal GPS coordinates (WGS84), stored as (lng, lat).
    boundary: Mapped[object] = mapped_column(
        Geometry("POLYGON", srid=4326, spatial_index=False)
    )
    area_acres: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # calculated, never typed
    crop_season_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("crop_seasons.id", ondelete="RESTRICT"), index=True
    )
    crop_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("crop_types.id", ondelete="RESTRICT"), index=True
    )
    district_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("districts.id", ondelete="RESTRICT"), index=True
    )
    sowing_date: Mapped[date | None] = mapped_column(Date)
