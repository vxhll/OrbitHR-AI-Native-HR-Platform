from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AttritionRecord(Base):
    __tablename__ = "attrition_records"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    employee_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("employees.employee_id"),
        nullable=False,
        unique=True,
    )

    employment_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    exit_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    exit_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    exit_reason: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    notice_period_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    rehire_eligible: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    attrited_within_180_days_label: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )