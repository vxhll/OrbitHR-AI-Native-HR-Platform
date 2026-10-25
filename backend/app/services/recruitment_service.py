from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.services.resume_screening_service import ResumeScreeningService
from app.services.resume_screening_summary_service import (
    ResumeScreeningSummaryService,
)
from datetime import UTC, datetime


class RecruitmentService:

    @staticmethod
    def create_job(db: Session, job_data: dict) -> Job:
        job = Job(**job_data)

        db.add(job)
        db.commit()
        db.refresh(job)

        return job

    @staticmethod
    def get_jobs(db: Session) -> list[Job]:
        result = db.execute(
            select(Job).order_by(Job.created_at.desc())
        )

        return list(result.scalars().all())

    @staticmethod
    def get_job(db: Session, job_id: int) -> Job | None:
        return db.get(Job, job_id)

    @staticmethod
    def create_candidate(
        db: Session,
        candidate_data: dict,
    ) -> Candidate:

        candidate = Candidate(**candidate_data)

        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        return candidate

    @staticmethod
    def get_candidates(db: Session) -> list[Candidate]:
        result = db.execute(
            select(Candidate).order_by(Candidate.created_at.desc())
        )

        return list(result.scalars().all())

    @staticmethod
    def get_candidate(
        db: Session,
        candidate_id: int,
    ) -> Candidate | None:

        return db.get(Candidate, candidate_id)

    @staticmethod
    def create_application(
        db: Session,
        application_data: dict,
    ) -> Application:

        job = db.get(Job, application_data["job_id"])

        if job is None:
            raise ValueError("Job not found")

        candidate = db.get(
            Candidate,
            application_data["candidate_id"],
        )

        if candidate is None:
            raise ValueError("Candidate not found")

        # ---------------------------------------------------------
        # STEP 1: Deterministic resume screening
        # ---------------------------------------------------------

        resume_text = candidate.resume_text or ""

        screening_result = ResumeScreeningService.screen_candidate(
            resume_text=resume_text,
            required_skills=job.required_skills,
            preferred_skills=job.preferred_skills,
            minimum_experience_years=job.minimum_experience_years,
        )

        # ---------------------------------------------------------
        # STEP 2: Generate AI screening explanation
        # ---------------------------------------------------------

        ai_summary = ResumeScreeningSummaryService.generate_summary(
            candidate_name=candidate.full_name,
            job_title=job.title,
            fit_score=screening_result["fit_score"],
            required_skill_score=screening_result["required_skill_score"],
            preferred_skill_score=screening_result["preferred_skill_score"],
            experience_score=screening_result["experience_score"],
            matched_required_skills=screening_result[
                "matched_required_skills"
            ],
            missing_required_skills=screening_result[
                "missing_required_skills"
            ],
            matched_preferred_skills=screening_result[
                "matched_preferred_skills"
            ],
            missing_preferred_skills=screening_result[
                "missing_preferred_skills"
            ],
            recommendation=screening_result["recommendation"],
        )

        # ---------------------------------------------------------
        # STEP 3: Persist application + screening result
        # ---------------------------------------------------------

        application = Application(
            **application_data,

            ai_fit_score=screening_result["fit_score"],

            required_skill_score=screening_result[
                "required_skill_score"
            ],

            preferred_skill_score=screening_result[
                "preferred_skill_score"
            ],

            experience_score=screening_result[
                "experience_score"
            ],

            matched_required_skills=", ".join(
                screening_result["matched_required_skills"]
            ),

            missing_required_skills=", ".join(
                screening_result["missing_required_skills"]
            ),

            matched_preferred_skills=", ".join(
                screening_result["matched_preferred_skills"]
            ),

            missing_preferred_skills=", ".join(
                screening_result["missing_preferred_skills"]
            ),

            ai_summary=ai_summary,

            ai_recommendation=screening_result[
                "recommendation"
            ],

            # Human approval remains mandatory.
            human_review_status="Pending",
        )

        db.add(application)
        db.commit()
        db.refresh(application)

        return application

    @staticmethod
    def get_applications(db: Session) -> list[Application]:
        result = db.execute(
            select(Application).order_by(
                Application.created_at.desc()
            )
        )

        return list(result.scalars().all())

    @staticmethod
    def get_application(
        db: Session,
        application_id: int,
    ) -> Application | None:

        return db.get(Application, application_id)
    @staticmethod
    def review_application(
        db: Session,
        application_id: int,
        review_status: str,
        reviewed_by: str,
        review_notes: str | None = None,
    ) -> Application | None:
        application = db.get(Application, application_id)

        if application is None:
            return None

        allowed_statuses = {
            "Approved",
            "Rejected",
            "Review Required",
        }

        if review_status not in allowed_statuses:
            raise ValueError(
                "Invalid review status. "
                "Use Approved, Rejected, or Review Required."
            )

        if application.human_review_status in {"Approved", "Rejected"}:
            raise ValueError(
                f"Application has already been finalized as "
                f"{application.human_review_status}."
            )

        application.human_review_status = review_status
        application.reviewed_by = reviewed_by
        application.reviewed_at = datetime.now(UTC)
        application.review_notes = review_notes

        db.commit()
        db.refresh(application)

        return application