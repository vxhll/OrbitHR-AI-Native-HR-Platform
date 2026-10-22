from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CandidateCreate(BaseModel):
    candidate_code: str = Field(min_length=1, max_length=30)
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=100)
    resume_filename: str | None = Field(default=None, max_length=255)
    resume_text: str | None = None


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_code: str
    full_name: str
    email: str
    phone: str | None
    location: str | None
    resume_filename: str | None
    resume_text: str | None
    created_at: datetime