from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.employee import Employee
from app.models.attrition_record import AttritionRecord
from app.models.attendance_login import AttendanceLogin
from app.models.payroll import Payroll
from app.models.performance_review import PerformanceReview
from app.models.engagement_survey import EngagementSurvey
from app.models.leave_record import LeaveRecord

router = APIRouter(
    prefix="/api/employees",
    tags=["Employees"],
)


@router.get("")
def get_employees(
    db: Session = Depends(get_db),
):
    employees = db.scalars(
        select(Employee)
        .order_by(Employee.employee_id)
    ).all()

    return {
        "count": len(employees),
        "employees": [
            {
                "employee_id": employee.employee_id,
                "full_name": employee.full_name,
                "gender": employee.gender,
                "age": employee.age,
                "department_id": employee.department_id,
                "job_role": employee.job_role,
                "job_level": employee.job_level,
                "work_location": employee.work_location,
                "hire_date": employee.hire_date,
                "tenure_years": employee.tenure_years_at_period_start,
                "education": employee.education,
                "marital_status": employee.marital_status,
                "annual_base_salary_inr": employee.annual_base_salary_inr,
                "manager_id": employee.manager_id,
            }
            for employee in employees
        ],
    }


@router.get("/{employee_id}")
def get_employee(
    employee_id: str,
    db: Session = Depends(get_db),
):
    employee = db.scalar(
        select(Employee).where(
            Employee.employee_id == employee_id
        )
    )

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail=f"Employee {employee_id} not found",
        )

    return {
        "employee_id": employee.employee_id,
        "full_name": employee.full_name,
        "gender": employee.gender,
        "age": employee.age,
        "department_id": employee.department_id,
        "job_role": employee.job_role,
        "job_level": employee.job_level,
        "work_location": employee.work_location,
        "hire_date": employee.hire_date,
        "tenure_years": employee.tenure_years_at_period_start,
        "education": employee.education,
        "marital_status": employee.marital_status,
        "annual_base_salary_inr": employee.annual_base_salary_inr,
        "manager_id": employee.manager_id,
    }
@router.get("/{employee_id}/profile")
def get_employee_profile(
    employee_id: str,
    db: Session = Depends(get_db),
):
    # ---------------------------------------------------------
    # Employee
    # ---------------------------------------------------------

    employee = db.scalar(
        select(Employee).where(
            Employee.employee_id == employee_id
        )
    )

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail=f"Employee {employee_id} not found",
        )

    # ---------------------------------------------------------
    # Attrition
    # ---------------------------------------------------------

    attrition = db.scalar(
        select(AttritionRecord).where(
            AttritionRecord.employee_id == employee_id
        )
    )

    # ---------------------------------------------------------
    # Attendance summary
    # ---------------------------------------------------------

    attendance_count = db.scalar(
        select(func.count(AttendanceLogin.id)).where(
            AttendanceLogin.employee_id == employee_id
        )
    )

    average_hours = db.scalar(
        select(func.avg(AttendanceLogin.hours_worked)).where(
            AttendanceLogin.employee_id == employee_id
        )
    )

    absent_days = db.scalar(
        select(func.count(AttendanceLogin.id)).where(
            AttendanceLogin.employee_id == employee_id,
            AttendanceLogin.status == "Absent",
        )
    )

    # ---------------------------------------------------------
    # Payroll summary
    # ---------------------------------------------------------

    payroll_count = db.scalar(
        select(func.count(Payroll.id)).where(
            Payroll.employee_id == employee_id
        )
    )

    latest_payroll = db.scalars(
        select(Payroll)
        .where(Payroll.employee_id == employee_id)
        .order_by(Payroll.pay_month.desc())
    ).first()

    # ---------------------------------------------------------
    # Performance
    # ---------------------------------------------------------

    performance_reviews = db.scalars(
        select(PerformanceReview)
        .where(
            PerformanceReview.employee_id == employee_id
        )
        .order_by(PerformanceReview.review_period.desc())
    ).all()

    # ---------------------------------------------------------
    # Engagement
    # ---------------------------------------------------------

    engagement_surveys = db.scalars(
        select(EngagementSurvey)
        .where(
            EngagementSurvey.employee_id == employee_id
        )
        .order_by(EngagementSurvey.survey_period.desc())
    ).all()

    # ---------------------------------------------------------
    # Leave
    # ---------------------------------------------------------

    leave_count = db.scalar(
        select(func.count(LeaveRecord.id)).where(
            LeaveRecord.employee_id == employee_id
        )
    )

    # ---------------------------------------------------------
    # Response
    # ---------------------------------------------------------

    return {
        "employee": {
            "employee_id": employee.employee_id,
            "full_name": employee.full_name,
            "gender": employee.gender,
            "age": employee.age,
            "department_id": employee.department_id,
            "job_role": employee.job_role,
            "job_level": employee.job_level,
            "work_location": employee.work_location,
            "hire_date": employee.hire_date,
            "tenure_years": employee.tenure_years_at_period_start,
            "education": employee.education,
            "marital_status": employee.marital_status,
            "annual_base_salary_inr": employee.annual_base_salary_inr,
            "manager_id": employee.manager_id,
        },

        "attrition": (
            {
                "employment_status": attrition.employment_status,
                "exit_date": attrition.exit_date,
                "exit_type": attrition.exit_type,
                "exit_reason": attrition.exit_reason,
                "attrited_within_180_days_label":
                    attrition.attrited_within_180_days_label,
            }
            if attrition
            else None
        ),

        "attendance": {
            "record_count": attendance_count or 0,
            "average_hours_worked": (
                round(float(average_hours), 2)
                if average_hours is not None
                else 0
            ),
            "absent_days": absent_days or 0,
        },

        "payroll": {
            "record_count": payroll_count or 0,
            "latest": (
                {
                    "pay_month": latest_payroll.pay_month,
                    "base_pay_inr": latest_payroll.base_pay_inr,
                    "bonus_inr": latest_payroll.bonus_inr,
                    "deductions_inr": latest_payroll.deductions_inr,
                    "net_pay_inr": latest_payroll.net_pay_inr,
                    "payment_date": latest_payroll.payment_date,
                }
                if latest_payroll
                else None
            ),
        },

        "performance": [
            {
                "review_period": review.review_period,
                "performance_rating_1to5":
                    review.performance_rating_1to5,
                "manager_feedback_score_1to10":
                    review.manager_feedback_score_1to10,
                "promotion_flag": review.promotion_flag,
            }
            for review in performance_reviews
        ],

        "engagement": [
            {
                "survey_period": survey.survey_period,
                "engagement_score_1to10":
                    survey.engagement_score_1to10,
                "job_satisfaction_score_1to10":
                    survey.job_satisfaction_score_1to10,
                "employee_nps": survey.employee_nps,
            }
            for survey in engagement_surveys
        ],

        "leave": {
            "record_count": leave_count or 0,
        },
    }