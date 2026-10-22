from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    onboarding_case_id: Mapped[int] = mapped_column(
        ForeignKey("onboarding_cases.id"),
        nullable=False,
    )

    task_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="Pending",
    )

    due_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )