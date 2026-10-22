from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ExitInterview(Base):
    __tablename__ = "exit_interviews"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    employee_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("employees.employee_id"),
        nullable=False,
    )

    interview_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    reason_for_leaving: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    feedback_on_management: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    feedback_on_work_environment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    feedback_on_career_growth: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    overall_satisfaction_1to10: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    would_recommend_company: Mapped[bool | None] = mapped_column(
        nullable=True,
    )

    additional_comments: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )