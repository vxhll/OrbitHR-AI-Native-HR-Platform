
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class HiringConfirmationRequest(BaseModel):
    """Employment details confirmed by HR before hiring."""

    gender: str = Field(min_length=1, max_length=20)
    age: int = Field(ge=18, le=100)
    job_level: str = Field(min_length=1, max_length=50)
    work_location: str = Field(min_length=1, max_length=100)
    joining_date: date
    tenure_years_at_period_start: float = Field(default=0, ge=0, le=60)
    education: str = Field(min_length=1, max_length=100)
    marital_status: str = Field(min_length=1, max_length=30)
    annual_base_salary_inr: int = Field(gt=0)
    manager_id: str | None = Field(default=None, max_length=20)


class HiringConfirmationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: int
    candidate_id: int
    employee_id: str
    employee_name: str
    onboarding_case_id: int
    joining_date: date
    status: str
