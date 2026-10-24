from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class OnboardingReminder(Base):
    __tablename__ = "onboarding_reminders"

    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "reminder_type",
            "reminder_date",
            name="uq_onboarding_reminder_task_type_date",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    task_id: Mapped[int] = mapped_column(
        ForeignKey("onboarding_tasks.id"),
        nullable=False,
        index=True,
    )

    recipient_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    reminder_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    reminder_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="Pending",
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    claim_token: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
