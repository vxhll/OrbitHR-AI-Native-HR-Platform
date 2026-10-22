from typing import Literal

from pydantic import BaseModel, Field


IntentType = Literal[
    "LEAVE",
    "HR_POLICY",
    "ONBOARDING",
    "PAYROLL",
    "RETENTION",
    "UNKNOWN",
    "HUMAN_ESCALATION",
]


class IntentClassificationRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class IntentClassificationResponse(BaseModel):
    question: str
    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
