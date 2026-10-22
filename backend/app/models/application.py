from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=False,
    )

    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id"),
        nullable=False,
    )

    application_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="Applied",
    )

    ai_fit_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    required_skill_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    preferred_skill_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    experience_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    matched_required_skills: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    missing_required_skills: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    matched_preferred_skills: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    missing_preferred_skills: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ai_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ai_recommendation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    human_review_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="Pending",
    )

    reviewed_by: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    review_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )