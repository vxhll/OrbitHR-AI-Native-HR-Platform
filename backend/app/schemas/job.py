from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    job_code: str = Field(min_length=1, max_length=30)
    title: str = Field(min_length=1, max_length=150)
    department_id: int
    description: str
    required_skills: str
    preferred_skills: str | None = None
    minimum_experience_years: int = Field(default=0, ge=0)
    status: str = Field(default="Open", max_length=30)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_code: str
    title: str
    department_id: int
    description: str
    required_skills: str
    preferred_skills: str | None
    minimum_experience_years: int
    status: str
    created_at: datetime