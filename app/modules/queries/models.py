from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, IdMixin


class Query(IdMixin, CreatedAtMixin, Base):
    """A farmer's question: text and/or a photo, voice note or video."""

    __tablename__ = "queries"
    __table_args__ = (
        CheckConstraint(
            "text IS NOT NULL OR image_url IS NOT NULL OR voice_url IS NOT NULL OR video_url IS NOT NULL",
            name="not_empty",
        ),
        Index("ix_queries_user_created", "user_id", "created_at"),  # "my queries, newest first"
    )

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    text: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    voice_url: Mapped[str | None] = mapped_column(String(500))
    video_url: Mapped[str | None] = mapped_column(String(500))

    # Assignment (filled in Step Q2) — on the query itself, no separate table
    assigned_to_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Answered = this is set. One column, so "done" and "when" can never disagree.
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def is_done(self) -> bool:
        return self.answered_at is not None
