from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.employee import Employee
from app.models.employee_exit import EmployeeExit
from app.security.dependencies import require_hr


router = APIRouter(
    prefix="/api/offboarding",
    tags=["Offboarding"],
)


class OffboardingCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=20)
    exit_date: date
    exit_type: str = Field(min_length=1, max_length=30)
    exit_reason: str = Field(min_length=1, max_length=200)
    notice_period_days: int | None = Field(default=None, ge=0)
    rehire_eligible: bool | None = None

    @field_validator("employee_id", "exit_type", "exit_reason")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class OffboardingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: str
    exit_date: date
    exit_type: str
    exit_reason: str
    notice_period_days: int | None
    rehire_eligible: bool | None
    status: str


@router.post(
    "",
    response_model=OffboardingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_hr)],
)
def create_offboarding(
    request: OffboardingCreate,
    db: Session = Depends(get_db),
):
    if request.exit_date > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exit date cannot be in the future",
        )

    employee = db.scalar(
        select(Employee).where(
            Employee.employee_id == request.employee_id
        )
    )

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    existing_exit = db.scalar(
        select(EmployeeExit).where(
            EmployeeExit.employee_id == request.employee_id
        )
    )

    if existing_exit is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An offboarding record already exists for this employee",
        )

    record = EmployeeExit(
        employee_id=request.employee_id,
        exit_date=request.exit_date,
        exit_type=request.exit_type,
        exit_reason=request.exit_reason,
        notice_period_days=request.notice_period_days,
        rehire_eligible=request.rehire_eligible,
        status="EXITED",
    )

    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An offboarding record already exists for this employee",
        )

    return record
