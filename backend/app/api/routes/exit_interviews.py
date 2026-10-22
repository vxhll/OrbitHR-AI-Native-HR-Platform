
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.employee import Employee
from app.models.employee_exit import EmployeeExit
from app.models.exit_interview import ExitInterview
from app.security.dependencies import require_hr


router = APIRouter(
    prefix="/api/exit-interviews",
    tags=["Exit Interviews"],
)


class ExitInterviewCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=20)
    interview_date: date
    reason_for_leaving: str = Field(min_length=1, max_length=200)
    feedback_on_management: str | None = None
    feedback_on_work_environment: str | None = None
    feedback_on_career_growth: str | None = None
    overall_satisfaction_1to10: int | None = Field(default=None, ge=1, le=10)
    would_recommend_company: bool | None = None
    additional_comments: str | None = None


class ExitInterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: str
    interview_date: date
    reason_for_leaving: str
    feedback_on_management: str | None
    feedback_on_work_environment: str | None
    feedback_on_career_growth: str | None
    overall_satisfaction_1to10: int | None
    would_recommend_company: bool | None
    additional_comments: str | None


@router.post(
    "",
    response_model=ExitInterviewResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_hr)],
)
def create_exit_interview(
    request: ExitInterviewCreate,
    db: Session = Depends(get_db),
):
    employee_id = request.employee_id.strip()
    reason = request.reason_for_leaving.strip()

    if not employee_id or not reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Employee ID and reason for leaving cannot be blank",
        )

    employee = db.scalar(
        select(Employee).where(Employee.employee_id == employee_id)
    )

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    exit_record = db.scalar(
        select(EmployeeExit).where(EmployeeExit.employee_id == employee_id)
    )

    if exit_record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An operational exit record is required before an exit interview",
        )

    interview = ExitInterview(
        employee_id=employee_id,
        interview_date=request.interview_date,
        reason_for_leaving=reason,
        feedback_on_management=request.feedback_on_management,
        feedback_on_work_environment=request.feedback_on_work_environment,
        feedback_on_career_growth=request.feedback_on_career_growth,
        overall_satisfaction_1to10=request.overall_satisfaction_1to10,
        would_recommend_company=request.would_recommend_company,
        additional_comments=request.additional_comments,
    )

    db.add(interview)
    db.commit()
    db.refresh(interview)

    return interview


@router.get(
    "/{interview_id}",
    response_model=ExitInterviewResponse,
    dependencies=[Depends(require_hr)],
)
def get_exit_interview(
    interview_id: int,
    db: Session = Depends(get_db),
):
    interview = db.get(ExitInterview, interview_id)

    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exit interview not found",
        )

    return interview
