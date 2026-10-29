from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Integer, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, IdMixin

ROLE_FARMER = "Farmer"
ROLE_RESPONSE_TEAM = "Response_Team"
ROLE_SUPER_ADMIN = "SuperAdmin"


class Role(IdMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True)


class User(IdMixin, CreatedAtMixin, Base):
    """Login is by mobile_number + password."""

    __tablename__ = "users"

    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("roles.id", ondelete="RESTRICT"), index=True
    )
    username: Mapped[str] = mapped_column(String(150))
    mobile_number: Mapped[str] = mapped_column(String(11), unique=True)
    email: Mapped[str | None] = mapped_column(String(254))
    password: Mapped[str] = mapped_column(String(255))  # a HASH, never the plain password

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    locality_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("localities.id", ondelete="RESTRICT"), index=True
    )

    role: Mapped[Role] = relationship(lazy="joined")

    __table_args__ = (
        CheckConstraint("cnic ~ '^[0-9]{13}$'", name="cnic_13_digits"),
    )

    cnic: Mapped[str | None] = mapped_column(String(13), unique=True)
    profile_picture: Mapped[str | None] = mapped_column(String(255))
    reference_code: Mapped[str] = mapped_column(String(8), unique=True)
    referred_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
