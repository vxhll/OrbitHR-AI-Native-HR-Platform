from typing import Any, TypedDict


class EmployeeSupportState(TypedDict, total=False):
    question: str

    employee_id: str
    prediction_date: str
    onboarding_case_id: int

    intent: str
    confidence: float
    intent_reason: str

    answer: str
    sources: list[dict[str, Any]]

    requires_human: bool
    error: str