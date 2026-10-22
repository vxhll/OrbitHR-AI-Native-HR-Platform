from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Payroll(Base):
    __tablename__ = "payroll"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    employee_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("employees.employee_id"),
        nullable=False,
    )

    pay_month: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
    )

    base_pay_inr: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    bonus_inr: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    deductions_inr: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    net_pay_inr: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    payment_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )