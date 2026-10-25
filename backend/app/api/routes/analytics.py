from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.attrition_record import AttritionRecord
from app.models.attendance_login import AttendanceLogin
from app.models.department import Department
from app.models.employee import Employee
from app.models.employee_exit import EmployeeExit
from app.models.engagement_survey import EngagementSurvey
from app.models.exit_interview import ExitInterview
from app.models.leave_record import LeaveRecord
from app.models.payroll import Payroll
from app.models.performance_review import PerformanceReview
from app.security.dependencies import require_hr


router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"],
)


@router.get(
    "/overview",
    dependencies=[Depends(require_hr)],
)
def get_organization_overview(
    db: Session = Depends(get_db),
):
    total_employees = db.scalar(
        select(func.count(Employee.id))
    ) or 0

    active_employees = db.scalar(
        select(func.count(AttritionRecord.id)).where(
            AttritionRecord.employment_status == "Active"
        )
    ) or 0

    exited_employees = db.scalar(
        select(func.count(AttritionRecord.id)).where(
            AttritionRecord.employment_status == "Exited"
        )
    ) or 0

    attrition_rate = (
        round((exited_employees / total_employees) * 100, 2)
        if total_employees
        else 0
    )

    average_age = db.scalar(
        select(func.avg(Employee.age))
    )

    average_salary = db.scalar(
        select(func.avg(Employee.annual_base_salary_inr))
    )

    average_attendance_hours = db.scalar(
        select(func.avg(AttendanceLogin.hours_worked))
    )

    average_performance = db.scalar(
        select(func.avg(PerformanceReview.performance_rating_1to5))
    )

    average_engagement = db.scalar(
        select(func.avg(EngagementSurvey.engagement_score_1to10))
    )

    return {
        "headcount": {
            "total": total_employees,
            "active": active_employees,
            "exited": exited_employees,
        },
        "attrition": {
            "exited_employees": exited_employees,
            "attrition_rate_percent": attrition_rate,
        },
        "workforce": {
            "average_age": (
                round(float(average_age), 2)
                if average_age is not None
                else 0
            ),
            "average_annual_salary_inr": (
                round(float(average_salary), 2)
                if average_salary is not None
                else 0
            ),
        },
        "workforce_signals": {
            "average_attendance_hours": (
                round(float(average_attendance_hours), 2)
                if average_attendance_hours is not None
                else 0
            ),
            "average_performance_rating": (
                round(float(average_performance), 2)
                if average_performance is not None
                else 0
            ),
            "average_engagement_score": (
                round(float(average_engagement), 2)
                if average_engagement is not None
                else 0
            ),
        },
    }


@router.get(
    "/departments",
    dependencies=[Depends(require_hr)],
)
def get_department_analytics(
    db: Session = Depends(get_db),
):
    departments = db.execute(
        select(
            Employee.department_id,
            func.count(Employee.id).label("headcount"),
        )
        .group_by(Employee.department_id)
        .order_by(Employee.department_id)
    ).all()

    results = []

    for department_id, headcount in departments:
        active_employees = db.scalar(
            select(func.count(AttritionRecord.id))
            .join(
                Employee,
                AttritionRecord.employee_id == Employee.employee_id,
            )
            .where(
                Employee.department_id == department_id,
                AttritionRecord.employment_status == "Active",
            )
        ) or 0

        exited_employees = db.scalar(
            select(func.count(AttritionRecord.id))
            .join(
                Employee,
                AttritionRecord.employee_id == Employee.employee_id,
            )
            .where(
                Employee.department_id == department_id,
                AttritionRecord.employment_status == "Exited",
            )
        ) or 0

        attrition_rate = (
            round((exited_employees / headcount) * 100, 2)
            if headcount
            else 0
        )

        average_engagement = db.scalar(
            select(func.avg(EngagementSurvey.engagement_score_1to10))
            .join(
                Employee,
                EngagementSurvey.employee_id == Employee.employee_id,
            )
            .where(Employee.department_id == department_id)
        )

        average_performance = db.scalar(
            select(func.avg(PerformanceReview.performance_rating_1to5))
            .join(
                Employee,
                PerformanceReview.employee_id == Employee.employee_id,
            )
            .where(Employee.department_id == department_id)
        )

        results.append(
            {
                "department_id": department_id,
                "headcount": headcount,
                "active_employees": active_employees,
                "exited_employees": exited_employees,
                "attrition_rate_percent": attrition_rate,
                "average_engagement_score": (
                    round(float(average_engagement), 2)
                    if average_engagement is not None
                    else 0
                ),
                "average_performance_rating": (
                    round(float(average_performance), 2)
                    if average_performance is not None
                    else 0
                ),
            }
        )

    return {
        "count": len(results),
        "departments": results,
    }


@router.get(
    "/attrition-features/{employee_id}",
    dependencies=[Depends(require_hr)],
)
def get_attrition_features(
    employee_id: str,
    db: Session = Depends(get_db),
):
    employee = db.scalar(
        select(Employee).where(Employee.employee_id == employee_id)
    )

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail=f"Employee {employee_id} not found",
        )

    attendance_count = db.scalar(
        select(func.count(AttendanceLogin.id)).where(
            AttendanceLogin.employee_id == employee_id
        )
    ) or 0

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
    ) or 0

    average_performance = db.scalar(
        select(func.avg(PerformanceReview.performance_rating_1to5)).where(
            PerformanceReview.employee_id == employee_id
        )
    )

    average_manager_feedback = db.scalar(
        select(func.avg(PerformanceReview.manager_feedback_score_1to10)).where(
            PerformanceReview.employee_id == employee_id
        )
    )

    promotion_count = db.scalar(
        select(func.count(PerformanceReview.id)).where(
            PerformanceReview.employee_id == employee_id,
            PerformanceReview.promotion_flag.is_(True),
        )
    ) or 0

    average_engagement = db.scalar(
        select(func.avg(EngagementSurvey.engagement_score_1to10)).where(
            EngagementSurvey.employee_id == employee_id
        )
    )

    average_job_satisfaction = db.scalar(
        select(func.avg(EngagementSurvey.job_satisfaction_score_1to10)).where(
            EngagementSurvey.employee_id == employee_id
        )
    )

    average_nps = db.scalar(
        select(func.avg(EngagementSurvey.employee_nps)).where(
            EngagementSurvey.employee_id == employee_id
        )
    )

    leave_count = db.scalar(
        select(func.count(LeaveRecord.id)).where(
            LeaveRecord.employee_id == employee_id
        )
    ) or 0

    total_leave_days = db.scalar(
        select(func.coalesce(func.sum(LeaveRecord.days), 0)).where(
            LeaveRecord.employee_id == employee_id
        )
    ) or 0

    payroll_count = db.scalar(
        select(func.count(Payroll.id)).where(
            Payroll.employee_id == employee_id
        )
    ) or 0

    attrition = db.scalar(
        select(AttritionRecord).where(
            AttritionRecord.employee_id == employee_id
        )
    )

    attrition_label = (
        attrition.attrited_within_180_days_label
        if attrition
        else None
    )

    return {
        "employee_id": employee.employee_id,
        "features": {
            "age": employee.age,
            "tenure_years": float(employee.tenure_years_at_period_start),
            "annual_base_salary_inr": employee.annual_base_salary_inr,
            "attendance_record_count": attendance_count,
            "average_hours_worked": (
                round(float(average_hours), 2)
                if average_hours is not None
                else 0
            ),
            "absent_days": absent_days,
            "average_performance_rating": (
                round(float(average_performance), 2)
                if average_performance is not None
                else 0
            ),
            "average_manager_feedback_score": (
                round(float(average_manager_feedback), 2)
                if average_manager_feedback is not None
                else 0
            ),
            "promotion_count": promotion_count,
            "average_engagement_score": (
                round(float(average_engagement), 2)
                if average_engagement is not None
                else 0
            ),
            "average_job_satisfaction_score": (
                round(float(average_job_satisfaction), 2)
                if average_job_satisfaction is not None
                else 0
            ),
            "average_employee_nps": (
                round(float(average_nps), 2)
                if average_nps is not None
                else 0
            ),
            "leave_record_count": leave_count,
            "total_leave_days": total_leave_days,
            "payroll_record_count": payroll_count,
        },
        "target": {
            "attrited_within_180_days_label": attrition_label,
        },
    }


@router.get(
    "/attrition-predict/{employee_id}",
    dependencies=[Depends(require_hr)],
)
def predict_attrition(
    employee_id: str,
    db: Session = Depends(get_db),
):
    from ml.attrition.prediction_service import AttritionPredictionService

    service = AttritionPredictionService()

    try:
        result = service.predict(
            db=db,
            employee_id=employee_id,
        )

        # Preserve the existing API response structure.
        result.pop("features", None)
        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Attrition model has not been trained yet",
        ) from exc


@router.get(
    "/attrition-predict-v3/{employee_id}",
    dependencies=[Depends(require_hr)],
)
def predict_attrition_v3(
    employee_id: str,
    prediction_date: date,
):
    from ml.attrition.event_based_prediction_service import (
        EventBasedPredictionService,
    )

    service = EventBasedPredictionService()

    try:
        return service.predict(
            employee_id=employee_id,
            prediction_date=prediction_date,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="V3 model or synthetic dataset is unavailable.",
        ) from exc



@router.get(
    "/exits",
    dependencies=[Depends(require_hr)],
)
def get_exit_analytics(db: Session = Depends(get_db)):
    total_exits = db.scalar(
        select(func.count(EmployeeExit.id))
    ) or 0

    exit_types = db.execute(
        select(
            EmployeeExit.exit_type,
            func.count(EmployeeExit.id).label("count"),
        )
        .group_by(EmployeeExit.exit_type)
        .order_by(EmployeeExit.exit_type)
    ).all()

    monthly_exits = db.execute(
        select(
            func.to_char(EmployeeExit.exit_date, "YYYY-MM").label("month"),
            func.count(EmployeeExit.id).label("count"),
        )
        .group_by(func.to_char(EmployeeExit.exit_date, "YYYY-MM"))
        .order_by(func.to_char(EmployeeExit.exit_date, "YYYY-MM"))
    ).all()

    interview_count = db.scalar(
        select(func.count(ExitInterview.id))
    ) or 0

    average_satisfaction = db.scalar(
        select(func.avg(ExitInterview.overall_satisfaction_1to10))
    )

    recommendation_responses = db.scalar(
        select(func.count(ExitInterview.id)).where(
            ExitInterview.would_recommend_company.is_not(None)
        )
    ) or 0

    recommendation_yes = db.scalar(
        select(func.count(ExitInterview.id)).where(
            ExitInterview.would_recommend_company.is_(True)
        )
    ) or 0

    recommendation_percentage = (
        round(
            (recommendation_yes / recommendation_responses) * 100,
            2,
        )
        if recommendation_responses
        else None
    )

    exit_reasons = db.execute(
        select(
            EmployeeExit.exit_reason,
            func.count(EmployeeExit.id).label("count"),
        )
        .group_by(EmployeeExit.exit_reason)
        .order_by(EmployeeExit.exit_reason)
    ).all()

    department_exits = db.execute(
        select(
            Department.id.label("department_id"),
            Department.name.label("department_name"),
            func.count(EmployeeExit.id).label("count"),
        )
        .join(
            Employee,
            Employee.department_id == Department.id,
        )
        .join(
            EmployeeExit,
            EmployeeExit.employee_id == Employee.employee_id,
        )
        .group_by(Department.id, Department.name)
        .order_by(Department.name)
    ).all()

    return {
        "total_recorded_exits": total_exits,
        "exit_type_breakdown": [
            {"exit_type": exit_type, "count": count}
            for exit_type, count in exit_types
        ],
        "exit_reason_breakdown": [
            {"exit_reason": reason, "count": count}
            for reason, count in exit_reasons
        ],
        "department_exit_breakdown": [
            {
                "department_id": department_id,
                "department_name": department_name,
                "count": count,
            }
            for department_id, department_name, count in department_exits
        ],
        "monthly_exit_trends": [
            {"month": month, "count": count}
            for month, count in monthly_exits
        ],
        "exit_interviews": {
            "total_interviews": interview_count,
            "average_satisfaction": (
                round(float(average_satisfaction), 2)
                if average_satisfaction is not None
                else None
            ),
            "recommendation_responses": recommendation_responses,
            "recommendation_yes": recommendation_yes,
            "recommendation_percentage": recommendation_percentage,
        },
    }
