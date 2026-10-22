from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class OnboardingCaseCreate(BaseModel):
    employee_id: str
    candidate_id: int | None = None
    joining_date: date


class OnboardingCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: str
    candidate_id: int | None
    status: str
    joining_date: date
    completion_percentage: int
    created_at: datetime
    completed_at: datetime | None


class OnboardingReadinessResponse(BaseModel):
    onboarding_case_id: int

    task_completion_percentage: int
    document_completion_percentage: int
    overall_completion_percentage: int

    total_tasks: int
    completed_tasks: int

    total_documents: int
    verified_documents: int
    pending_documents: int
    rejected_documents: int
    submitted_documents: int

    onboarding_status: str
    onboarding_ready: bool