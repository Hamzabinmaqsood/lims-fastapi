from sqlalchemy import ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CropSeason(Base):
    """Rabi, Kharif, ..."""

    __tablename__ = "crop_seasons"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


class CropType(Base):
    """Wheat, Cotton, Rice, ... Each belongs to one season."""

    __tablename__ = "crop_types"
    __table_args__ = (UniqueConstraint("season_id", "name"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    season_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("crop_seasons.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
