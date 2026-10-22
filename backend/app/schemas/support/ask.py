from typing import Any

from pydantic import BaseModel, Field

from datetime import date

class HRSupportQuestion(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=1000,
    )
    employee_id: str | None = None
    onboarding_case_id: int | None = None
    prediction_date: date | None = None


class HRSupportSource(BaseModel):
    source: str | None = None
    policy_id: str | None = None
    section: str | None = None
    type: str | None = None
    employee_id: str | None = None
    pay_month: str | None = None
    payroll_id: int | None = None
    onboarding_case_id: int | None = None


class HRSupportResponse(BaseModel):
    question: str
    intent: str
    confidence: float
    answer: str
    requires_human: bool
    sources: list[dict[str, Any]]