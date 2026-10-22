from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class OnboardingTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    onboarding_case_id: int
    task_code: str
    title: str
    description: str | None
    category: str
    required: bool
    status: str
    due_date: date | None
    completed_at: datetime | None
    created_at: datetime