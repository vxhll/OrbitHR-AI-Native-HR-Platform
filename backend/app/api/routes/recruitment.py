from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db

from app.schemas import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationReviewRequest,
    CandidateCreate,
    CandidateResponse,
    JobCreate,
    JobResponse,
)
from app.schemas.hiring import (
    HiringConfirmationRequest,
    HiringConfirmationResponse,
)
from app.services.recruitment_service import RecruitmentService
from app.services.hiring_service import HiringService
from app.models.auth.user import User
from app.security.dependencies import require_recruiter, require_hr


router = APIRouter(
    prefix="/api/recruitment",
    tags=["Recruitment"],
    dependencies=[Depends(require_recruiter)],
)


# -------------------------------------------------------------------
# JOBS
# -------------------------------------------------------------------

@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job(
    job_data: JobCreate,
    db: Session = Depends(get_db),
):
    return RecruitmentService.create_job(
        db,
        job_data.model_dump(),
    )


@router.get(
    "/jobs",
    response_model=list[JobResponse],
)
def get_jobs(
    db: Session = Depends(get_db),
):
    return RecruitmentService.get_jobs(db)


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
):
    job = RecruitmentService.get_job(db, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return job


# -------------------------------------------------------------------
# CANDIDATES
# -------------------------------------------------------------------

@router.post(
    "/candidates",
    response_model=CandidateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_candidate(
    candidate_data: CandidateCreate,
    db: Session = Depends(get_db),
):
    return RecruitmentService.create_candidate(
        db,
        candidate_data.model_dump(),
    )


@router.get(
    "/candidates",
    response_model=list[CandidateResponse],
)
def get_candidates(
    db: Session = Depends(get_db),
):
    return RecruitmentService.get_candidates(db)


@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateResponse,
)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
):
    candidate = RecruitmentService.get_candidate(
        db,
        candidate_id,
    )

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )

    return candidate


# -------------------------------------------------------------------
# APPLICATIONS
# -------------------------------------------------------------------

@router.post(
    "/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_application(
    application_data: ApplicationCreate,
    db: Session = Depends(get_db),
):
    return RecruitmentService.create_application(
        db,
        application_data.model_dump(),
    )


@router.get(
    "/applications",
    response_model=list[ApplicationResponse],
)
def get_applications(
    db: Session = Depends(get_db),
):
    return RecruitmentService.get_applications(db)


@router.get(
    "/applications/{application_id}",
    response_model=ApplicationResponse,
)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
):
    application = RecruitmentService.get_application(
        db,
        application_id,
    )

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    return application

@router.post(
    "/applications/{application_id}/review",
    response_model=ApplicationResponse,
)
def review_application(
    application_id: int,
    review_data: ApplicationReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    try:
        application = RecruitmentService.review_application(
            db=db,
            application_id=application_id,
            review_status=review_data.review_status,
            reviewed_by=current_user.email,
            review_notes=review_data.review_notes,
        )

        if application is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )

        return application

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

# -------------------------------------------------------------------
# HIRING CONFIRMATION — HR / ADMIN ONLY
# -------------------------------------------------------------------

@router.post(
    "/applications/{application_id}/hire",
    response_model=HiringConfirmationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_hr)],
)
def confirm_hire(
    application_id: int,
    hiring_data: HiringConfirmationRequest,
    db: Session = Depends(get_db),
):
    try:
        return HiringService.confirm_hire(
            db=db,
            application_id=application_id,
            employment_details=hiring_data.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
