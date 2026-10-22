from datetime import date, time

from sqlalchemy import Date, ForeignKey, Numeric, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AttendanceLogin(Base):
    __tablename__ = "attendance_login"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    employee_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("employees.employee_id"),
        nullable=False,
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    login_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    logout_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    hours_worked: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )