from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.attendance_login import AttendanceLogin
from app.models.performance_review import PerformanceReview
from app.models.engagement_survey import EngagementSurvey
from app.models.leave_record import LeaveRecord
from app.models.payroll import Payroll

FEATURE_COLUMNS = [
    "age",
    "tenure_years",
    "annual_base_salary_inr",
    "attendance_record_count",
    "average_hours_worked",
    "absent_days",
    "average_performance_rating",
    "average_manager_feedback_score",
    "promotion_count",
    "average_engagement_score",
    "average_job_satisfaction_score",
    "average_employee_nps",
    "leave_record_count",
    "total_leave_days",
    "payroll_record_count",
]


def build_attrition_features(
    db: Session,
    employee_id: str,
) -> dict:

    employee = db.scalar(
        select(Employee).where(
            Employee.employee_id == employee_id
        )
    )

    if employee is None:
        raise ValueError(
            f"Employee {employee_id} not found"
        )

    attendance_records = db.scalars(
        select(AttendanceLogin).where(
            AttendanceLogin.employee_id == employee_id
        )
    ).all()

    attendance_count = len(attendance_records)

    average_hours = (
        sum(
            float(record.hours_worked)
            for record in attendance_records
            if record.hours_worked is not None
        ) / attendance_count
        if attendance_count
        else 0
    )

    absent_days = sum(
        1
        for record in attendance_records
        if record.status == "Absent"
    )

    performance_records = db.scalars(
        select(PerformanceReview).where(
            PerformanceReview.employee_id == employee_id
        )
    ).all()

    performance_count = len(performance_records)

    average_performance = (
        sum(
            float(record.performance_rating_1to5)
            for record in performance_records
            if record.performance_rating_1to5 is not None
        ) / performance_count
        if performance_count
        else 0
    )

    average_manager_feedback = (
        sum(
            float(record.manager_feedback_score_1to10)
            for record in performance_records
            if record.manager_feedback_score_1to10 is not None
        ) / performance_count
        if performance_count
        else 0
    )

    promotion_count = sum(
        1
        for record in performance_records
        if record.promotion_flag
    )

    engagement_records = db.scalars(
        select(EngagementSurvey).where(
            EngagementSurvey.employee_id == employee_id
        )
    ).all()

    engagement_count = len(engagement_records)

    average_engagement = (
        sum(
            float(record.engagement_score_1to10)
            for record in engagement_records
            if record.engagement_score_1to10 is not None
        ) / engagement_count
        if engagement_count
        else 0
    )

    average_job_satisfaction = (
        sum(
            float(record.job_satisfaction_score_1to10)
            for record in engagement_records
            if record.job_satisfaction_score_1to10 is not None
        ) / engagement_count
        if engagement_count
        else 0
    )

    average_nps = (
        sum(
            float(record.employee_nps)
            for record in engagement_records
            if record.employee_nps is not None
        ) / engagement_count
        if engagement_count
        else 0
    )

    leave_records = db.scalars(
        select(LeaveRecord).where(
            LeaveRecord.employee_id == employee_id
        )
    ).all()

    leave_record_count = len(leave_records)

    total_leave_days = sum(
        int(record.days)
        for record in leave_records
        if record.days is not None
    )

    payroll_records = db.scalars(
        select(Payroll).where(
            Payroll.employee_id == employee_id
        )
    ).all()

    payroll_record_count = len(payroll_records)

    return {
        "age": employee.age,
        "tenure_years": float(
            employee.tenure_years_at_period_start
        ),
        "annual_base_salary_inr": employee.annual_base_salary_inr,
        "attendance_record_count": attendance_count,
        "average_hours_worked": average_hours,
        "absent_days": absent_days,
        "average_performance_rating": average_performance,
        "average_manager_feedback_score": average_manager_feedback,
        "promotion_count": promotion_count,
        "average_engagement_score": average_engagement,
        "average_job_satisfaction_score": average_job_satisfaction,
        "average_employee_nps": average_nps,
        "leave_record_count": leave_record_count,
        "total_leave_days": total_leave_days,
        "payroll_record_count": payroll_record_count,
    }