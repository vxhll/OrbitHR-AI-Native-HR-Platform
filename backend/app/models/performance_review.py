from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class PerformanceReview(Base):
    __tablename__ = "performance_reviews"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    employee_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("employees.employee_id"),
        nullable=False,
    )

    review_period: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    performance_rating_1to5: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    manager_feedback_score_1to10: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    promotion_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )