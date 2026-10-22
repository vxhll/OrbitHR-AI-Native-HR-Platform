from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class LeaveRecord(Base):
    __tablename__ = "leave_records"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    employee_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("employees.employee_id"),
        nullable=False,
    )

    leave_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    approval_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    approved_by: Mapped[str | None] = mapped_column(
        String(20),
        ForeignKey("employees.employee_id"),
        nullable=True,
    )