from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, IdMixin

NOT_EMPTY = "text IS NOT NULL OR image_url IS NOT NULL OR voice_url IS NOT NULL OR video_url IS NOT NULL"


class ContentMixin:
    """The message content shared by queries, answers and their old versions."""

    text: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    voice_url: Mapped[str | None] = mapped_column(String(500))
    video_url: Mapped[str | None] = mapped_column(String(500))


class Query(IdMixin, CreatedAtMixin, ContentMixin, Base):
    """A farmer's question: text and/or a photo, voice note or video."""

    __tablename__ = "queries"
    __table_args__ = (
        CheckConstraint(NOT_EMPTY, name="not_empty"),
        CheckConstraint("status IN ('pending', 'answered')", name="status_valid"),
        # status is redundant with answered_at → the database keeps them in sync
        CheckConstraint("(status = 'answered') = (answered_at IS NOT NULL)", name="status_matches_answered_at"),
        Index("ix_queries_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(10), default="pending", server_default="pending", index=True)
    assigned_to_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    response: Mapped["QueryResponse | None"] = relationship(lazy="selectin", uselist=False)

    @property
    def is_done(self) -> bool:
        return self.status == "answered"


class QueryResponse(IdMixin, CreatedAtMixin, ContentMixin, Base):
    """The team's answer to a query."""

    __tablename__ = "query_responses"
    __table_args__ = (
        UniqueConstraint("query_id"),
        CheckConstraint(NOT_EMPTY, name="not_empty"),
        CheckConstraint("status IN ('sent', 'edited')", name="status_valid"),
    )

    query_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("queries.id", ondelete="CASCADE"))
    responder_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(10), default="sent", server_default="sent")


class QueryVersion(IdMixin, CreatedAtMixin, ContentMixin, Base):
    """An earlier version of a query, saved just before it was edited."""

    __tablename__ = "query_versions"
    __table_args__ = (Index("ix_query_versions_query_created", "query_id", "created_at"),)

    query_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("queries.id", ondelete="CASCADE"))


class ResponseVersion(IdMixin, CreatedAtMixin, ContentMixin, Base):
    """An earlier version of an answer, saved just before it was edited."""

    __tablename__ = "response_versions"
    __table_args__ = (Index("ix_response_versions_response_created", "response_id", "created_at"),)

    response_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("query_responses.id", ondelete="CASCADE"))
