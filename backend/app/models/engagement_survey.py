from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class EngagementSurvey(Base):
    __tablename__ = "engagement_surveys"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    employee_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("employees.employee_id"),
        nullable=False,
    )

    survey_period: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
    )

    engagement_score_1to10: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    job_satisfaction_score_1to10: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    employee_nps: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )