from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ml.attrition.feature_service import build_attrition_features

from app.db.database import get_db
from app.models.employee import Employee
from app.models.attrition_record import AttritionRecord
from app.models.attendance_login import AttendanceLogin
from app.models.performance_review import PerformanceReview
from app.models.engagement_survey import EngagementSurvey
from app.models.leave_record import LeaveRecord
from app.models.payroll import Payroll
import os
import joblib
import pandas as pd

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"],
)


@router.get("/overview")
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
@router.get("/departments")
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
@router.get("/attrition-features/{employee_id}")
def get_attrition_features(
    employee_id: str,
    db: Session = Depends(get_db),
):
    employee = db.scalar(
        select(Employee).where(Employee.employee_id == employee_id)
    )

    if employee is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail=f"Employee {employee_id} not found",
        )

    # Attendance features
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

    # Performance features
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
            PerformanceReview.promotion_flag == True,
        )
    ) or 0

    # Engagement features
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

    # Leave features
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

    # Payroll features
    payroll_count = db.scalar(
        select(func.count(Payroll.id)).where(
            Payroll.employee_id == employee_id
        )
    ) or 0

    # Historical attrition label
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
@router.get("/attrition-predict/{employee_id}")
def predict_attrition(
    employee_id: str,
    db: Session = Depends(get_db),
):
    # -------------------------
    # Build features using the
    # shared feature service
    # -------------------------

    try:
        feature_data = build_attrition_features(
            db,
            employee_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    # -------------------------
    # Feature vector
    # -------------------------

    feature_columns = [
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

    features = pd.DataFrame(
        [[feature_data[column] for column in feature_columns]],
        columns=feature_columns,
    )

    # -------------------------
    # Load trained model
    # -------------------------

    project_root = r"D:\OrbitHR-AI-Native-HR-Platform"

    model_path = os.path.join(
        project_root,
        "ml",
        "attrition",
        "attrition_logistic_regression.joblib",
    )

    if not os.path.exists(model_path):
        raise HTTPException(
            status_code=500,
            detail="Attrition model has not been trained yet",
        )

    model = joblib.load(model_path)

    # -------------------------
    # Prediction
    # -------------------------

    prediction = int(
        model.predict(features)[0]
    )

    probability = float(
        model.predict_proba(features)[0][1]
    )

    probability_percent = round(
        probability * 100,
        2,
    )

    # -------------------------
    # Risk classification
    # -------------------------

    if probability >= 0.70:
        risk_level = "High"
    elif probability >= 0.40:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    # -------------------------
    # Response
    # -------------------------

    return {
        "employee_id": employee_id,
        "prediction": {
            "attrition_probability_percent": probability_percent,
            "risk_level": risk_level,
            "predicted_attrition": bool(prediction),
        },
        "model": {
            "name": "Logistic Regression",
            "version": "baseline-1.0",
        },
    }