from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    employee_id: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    unique=True,
)

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    gender: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    age: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id"),
        nullable=False,
    )

    job_role: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    job_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    work_location: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    hire_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    tenure_years_at_period_start: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    education: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    marital_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    annual_base_salary_inr: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    manager_id: Mapped[str | None] = mapped_column(
        String(20),
        ForeignKey("employees.employee_id"),
        nullable=True,
    )