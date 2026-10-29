from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CoordinatesMixin:
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))


class Province(CoordinatesMixin, Base):
    __tablename__ = "provinces"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


class District(CoordinatesMixin, Base):
    __tablename__ = "districts"
    __table_args__ = (UniqueConstraint("province_id", "name"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    province_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("provinces.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))


class Tehsil(CoordinatesMixin, Base):
    __tablename__ = "tehsils"
    __table_args__ = (UniqueConstraint("district_id", "name"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    district_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("districts.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))


class Locality(CoordinatesMixin, Base):
    """A city or village inside a tehsil."""

    __tablename__ = "localities"
    __table_args__ = (
        UniqueConstraint("tehsil_id", "name"),
        CheckConstraint("kind IN ('city', 'village')", name="kind_valid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tehsil_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("tehsils.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(7))  # 'city' or 'village'
