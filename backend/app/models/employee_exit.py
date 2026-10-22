
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class EmployeeExit(Base):
    __tablename__ = "employee_exits"

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

    exit_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    exit_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    exit_reason: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    notice_period_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    rehire_eligible: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="EXITED",
    )
