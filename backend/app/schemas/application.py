from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ApplicationCreate(BaseModel):
    job_id: int
    candidate_id: int
    application_status: str = Field(
        default="Applied",
        max_length=30,
    )


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    candidate_id: int

    application_status: str

    ai_fit_score: float | None
    required_skill_score: float | None
    preferred_skill_score: float | None
    experience_score: float | None

    matched_required_skills: str | None
    missing_required_skills: str | None

    matched_preferred_skills: str | None
    missing_preferred_skills: str | None

    ai_summary: str | None
    ai_recommendation: str | None

    human_review_status: str

    reviewed_by: str | None
    reviewed_at: datetime | None
    review_notes: str | None

    created_at: datetime

class ApplicationReviewRequest(BaseModel):
    review_status: Literal[
        "Approved",
        "Rejected",
        "Review Required",
    ]
    review_notes: str | None = None
