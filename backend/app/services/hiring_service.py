import re

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.candidate import Candidate
from app.models.department import Department
from app.models.employee import Employee
from app.models.job import Job
from app.models.onboarding import OnboardingCase
from app.services.onboarding_service import OnboardingService


class HiringService:
    @staticmethod
    def confirm_hire(
        db: Session,
        application_id: int,
        employment_details: dict,
    ) -> dict:
        try:
            application = db.execute(
                select(Application)
                .where(Application.id == application_id)
                .with_for_update()
            ).scalar_one_or_none()

            if application is None:
                raise ValueError("Application not found")

            if application.human_review_status != "Approved":
                raise ValueError(
                    "Application must be approved before hiring confirmation"
                )

            if application.application_status == "Hired":
                raise ValueError("Application has already been hired")

            candidate = db.get(Candidate, application.candidate_id)
            job = db.get(Job, application.job_id)

            if candidate is None:
                raise ValueError("Candidate not found")

            if job is None:
                raise ValueError("Job not found")

            department = db.get(Department, job.department_id)

            if department is None:
                raise ValueError("Job department not found")

            existing_case = db.execute(
                select(OnboardingCase).where(
                    OnboardingCase.candidate_id == candidate.id
                )
            ).scalar_one_or_none()

            if existing_case is not None:
                raise ValueError(
                    "An onboarding case already exists for this candidate"
                )

                        # Serialize hiring transactions before checking for duplicates.
            # This ensures concurrent requests for the same candidate cannot
            # both pass the onboarding-case check.
            db.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": 73190521},
            )

            existing_case = db.execute(
                select(OnboardingCase).where(
                    OnboardingCase.candidate_id == candidate.id
                )
            ).scalar_one_or_none()

            if existing_case is not None:
                raise ValueError(
                    "An onboarding case already exists for this candidate"
                )

            employee_numbers = db.execute(
                select(Employee.employee_id)
            ).scalars().all()

            numeric_ids = [
                int(match.group(1))
                for value in employee_numbers
                if (match := re.fullmatch(r"EMP(\d+)", value))
            ]

            next_number = max(numeric_ids, default=0) + 1
            employee_id = f"EMP{next_number:04d}"

            joining_date = employment_details["joining_date"]

            employee = Employee(
                employee_id=employee_id,
                full_name=candidate.full_name,
                department_id=department.id,
                job_role=job.title,
                gender=employment_details["gender"],
                age=employment_details["age"],
                job_level=employment_details["job_level"],
                work_location=employment_details["work_location"],
                hire_date=joining_date,
                tenure_years_at_period_start=employment_details[
                    "tenure_years_at_period_start"
                ],
                education=employment_details["education"],
                marital_status=employment_details["marital_status"],
                annual_base_salary_inr=employment_details[
                    "annual_base_salary_inr"
                ],
                manager_id=employment_details.get("manager_id"),
            )

            db.add(employee)
            db.flush()

            onboarding_case = OnboardingCase(
                employee_id=employee.employee_id,
                candidate_id=candidate.id,
                status="Not Started",
                joining_date=joining_date,
                completion_percentage=0,
            )

            db.add(onboarding_case)
            db.flush()

            OnboardingService._generate_documents(
                db=db,
                onboarding_case_id=onboarding_case.id,
            )

            OnboardingService._generate_tasks(
                db=db,
                onboarding_case_id=onboarding_case.id,
                department=department.name,
                job_role=job.title,
                job_level=employee.job_level,
                joining_date=joining_date,
            )

            application.application_status = "Hired"

            db.commit()
            db.refresh(employee)
            db.refresh(onboarding_case)

            return {
                "application_id": application.id,
                "candidate_id": candidate.id,
                "employee_id": employee.employee_id,
                "employee_name": employee.full_name,
                "onboarding_case_id": onboarding_case.id,
                "joining_date": onboarding_case.joining_date,
                "status": "Hired",
            }

        except Exception:
            db.rollback()
            raise
