from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OnboardingDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    onboarding_case_id: int
    document_type: str
    status: str
    file_name: str | None
    submitted_at: datetime | None
    verified_at: datetime | None
    created_at: datetime


class OnboardingDocumentVerificationRequest(BaseModel):
    status: str


class OnboardingDocumentProgressResponse(BaseModel):
    onboarding_case_id: int
    total_documents: int
    submitted_documents: int
    verified_documents: int
    rejected_documents: int
    pending_documents: int
    completion_percentage: int