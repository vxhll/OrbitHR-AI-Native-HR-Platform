from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.attendance_login import AttendanceLogin
from app.models.performance_review import PerformanceReview
from app.models.engagement_survey import EngagementSurvey


def build_attrition_features(
    db: Session,
    employee_id: str,
) -> dict[str, Any]:
    """
    Build the feature vector used by the attrition prediction model.

    Features are derived from the employee's HR records.
    """

    employee = (
        db.query(Employee)
        .filter(Employee.employee_id == employee_id)
        .first()
    )

    if employee is None:
        raise ValueError(f"Employee {employee_id} not found")

    # ---------------------------------------------------------
    # Attendance
    # ---------------------------------------------------------
    attendance_days = (
        db.query(func.count(AttendanceLogin.id))
        .filter(AttendanceLogin.employee_id == employee_id)
        .scalar()
        or 0
    )

    late_days = (
        db.query(func.count(AttendanceLogin.id))
        .filter(
            AttendanceLogin.employee_id == employee_id,
            AttendanceLogin.status == "Late",
        )
        .scalar()
        or 0
    )

    late_ratio = (
        late_days / attendance_days
        if attendance_days > 0
        else 0.0
    )

    # ---------------------------------------------------------
    # Performance
    # ---------------------------------------------------------
    performance_score = (
        db.query(func.avg(PerformanceReview.performance_rating_1to5))
        .filter(PerformanceReview.employee_id == employee_id)
        .scalar()
    )

    performance_score = float(performance_score or 0.0)

    # ---------------------------------------------------------
    # Engagement
    # ---------------------------------------------------------
    engagement_score = (
        db.query(func.avg(EngagementSurvey.engagement_score_1to10))
        .filter(EngagementSurvey.employee_id == employee_id)
        .scalar()
    )

    engagement_score = float(engagement_score or 0.0)

    # ---------------------------------------------------------
    # Employee-level features
    # ---------------------------------------------------------
    tenure = float(
        employee.tenure_years_at_period_start or 0.0
    )

    age = int(employee.age or 0)

    salary = float(
        employee.annual_base_salary_inr or 0
    )

    features = {
        "age": age,
        "tenure_years": tenure,
        "annual_base_salary_inr": salary,
        "attendance_days": int(attendance_days),
        "late_ratio": round(late_ratio, 4),
        "performance_score": round(performance_score, 4),
        "engagement_score": round(engagement_score, 4),
    }

    return features