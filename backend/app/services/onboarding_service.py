from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.employee import Employee
from app.models.onboarding import (
    OnboardingCase,
    OnboardingDocument,
    OnboardingTask,
)


# ============================================================
# Document storage configuration
# ============================================================

UPLOAD_DIR = Path("storage/onboarding")

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


class OnboardingService:

    # ========================================================
    # Employee
    # ========================================================

    @staticmethod
    def get_employee(
        db: Session,
        employee_id: str,
    ) -> Employee | None:

        result = db.execute(
            select(Employee).where(
                Employee.employee_id == employee_id
            )
        )

        return result.scalar_one_or_none()

    # ========================================================
    # Onboarding Case
    # ========================================================

    @staticmethod
    def create_onboarding_case(
        db: Session,
        employee_id: str,
        candidate_id: int | None,
        joining_date: date,
    ) -> OnboardingCase:

        employee = OnboardingService.get_employee(
            db=db,
            employee_id=employee_id,
        )

        if employee is None:
            raise ValueError("Employee not found")

        existing_case = db.execute(
            select(OnboardingCase).where(
                OnboardingCase.employee_id == employee_id
            )
        ).scalar_one_or_none()

        if existing_case is not None:
            raise ValueError(
                "An onboarding case already exists for this employee"
            )

        onboarding_case = OnboardingCase(
            employee_id=employee_id,
            candidate_id=candidate_id,
            status="Not Started",
            joining_date=joining_date,
            completion_percentage=0,
        )

        db.add(onboarding_case)
        db.flush()

        department = db.get(
            Department,
            employee.department_id,
        )

        department_name = (
            department.name
            if department is not None
            else ""
        )

        OnboardingService._generate_documents(
            db=db,
            onboarding_case_id=onboarding_case.id,
        )

        OnboardingService._generate_tasks(
            db=db,
            onboarding_case_id=onboarding_case.id,
            department=department_name,
            job_role=employee.job_role,
            job_level=employee.job_level,
            joining_date=joining_date,
        )

        db.commit()
        db.refresh(onboarding_case)

        return onboarding_case

    @staticmethod
    def get_onboarding_case(
        db: Session,
        onboarding_case_id: int,
    ) -> OnboardingCase | None:

        return db.get(
            OnboardingCase,
            onboarding_case_id,
        )

    # ========================================================
    # Adaptive Document Generation
    # ========================================================

    @staticmethod
    def _generate_documents(
        db: Session,
        onboarding_case_id: int,
    ) -> None:

        required_documents = [
            "Identity Proof",
            "Address Proof",
            "Bank Account Details",
            "Tax Declaration",
        ]

        for document_type in required_documents:

            document = OnboardingDocument(
                onboarding_case_id=onboarding_case_id,
                document_type=document_type,
                status="Pending",
            )

            db.add(document)

    # ========================================================
    # Adaptive Task Generation
    # ========================================================

    @staticmethod
    def _generate_tasks(
        db: Session,
        onboarding_case_id: int,
        department: str,
        job_role: str,
        job_level: str,
        joining_date: date,
    ) -> None:

        common_tasks = [
            (
                "HR-001",
                "Complete employee profile",
                "Complete personal and employment information.",
                "HR",
                True,
                2,
            ),
            (
                "HR-002",
                "Acknowledge employee handbook",
                "Review and acknowledge the employee handbook.",
                "Policy",
                True,
                3,
            ),
            (
                "SEC-001",
                "Complete security awareness training",
                "Complete mandatory information security training.",
                "Security",
                True,
                5,
            ),
            (
                "HR-003",
                "Meet HR representative",
                "Complete the initial HR orientation.",
                "HR",
                True,
                5,
            ),
        ]

        role_tasks = []

        department_text = str(department).lower()
        role_text = str(job_role).lower()
        level_text = str(job_level).lower()

        # Engineering / technical employees
        if (
            "engineering" in department_text
            or "developer" in role_text
            or "engineer" in role_text
            or "tech lead" in role_text
        ):
            role_tasks.extend(
                [
                    (
                        "ENG-001",
                        "Set up development environment",
                        "Configure required development tools and repositories.",
                        "Role",
                        True,
                        5,
                    ),
                    (
                        "ENG-002",
                        "Complete engineering onboarding",
                        "Review engineering standards and development workflow.",
                        "Role",
                        True,
                        7,
                    ),
                ]
            )

        # Managers / team leads
        if (
            "manager" in level_text
            or "lead" in role_text
        ):
            role_tasks.append(
                (
                    "MGR-001",
                    "Complete manager orientation",
                    "Review people-management responsibilities and HR processes.",
                    "Leadership",
                    True,
                    7,
                )
            )

        # HR employees
        if "hr" in department_text:
            role_tasks.append(
                (
                    "HR-004",
                    "Review HR operations workflow",
                    "Review internal HR systems and operational procedures.",
                    "Role",
                    True,
                    7,
                )
            )

        for (
            task_code,
            title,
            description,
            category,
            required,
            days_after_joining,
        ) in common_tasks + role_tasks:

            task = OnboardingTask(
                onboarding_case_id=onboarding_case_id,
                task_code=task_code,
                title=title,
                description=description,
                category=category,
                required=required,
                status="Pending",
                due_date=joining_date + timedelta(
                    days=days_after_joining
                ),
            )

            db.add(task)

    # ========================================================
    # Task Retrieval
    # ========================================================

    @staticmethod
    def get_tasks(
        db: Session,
        onboarding_case_id: int,
    ) -> list[OnboardingTask]:

        result = db.execute(
            select(OnboardingTask)
            .where(
                OnboardingTask.onboarding_case_id
                == onboarding_case_id
            )
            .order_by(OnboardingTask.id)
        )

        return list(result.scalars().all())

    # ========================================================
    # Task Completion
    # ========================================================

    @staticmethod
    def complete_task(
        db: Session,
        task_id: int,
    ) -> OnboardingTask | None:

        task = db.get(
            OnboardingTask,
            task_id,
        )

        if task is None:
            return None

        task.status = "Completed"
        task.completed_at = datetime.utcnow()

        OnboardingService._recalculate_progress(
            db=db,
            onboarding_case_id=task.onboarding_case_id,
        )

        db.commit()
        db.refresh(task)

        return task

    # ========================================================
    # Task Progress
    # ========================================================

    @staticmethod
    def _recalculate_progress(
        db: Session,
        onboarding_case_id: int,
    ) -> None:

        tasks = OnboardingService.get_tasks(
            db=db,
            onboarding_case_id=onboarding_case_id,
        )

        if not tasks:
            return

        completed_tasks = [
            task
            for task in tasks
            if task.status == "Completed"
        ]

        percentage = round(
            len(completed_tasks)
            / len(tasks)
            * 100
        )

        onboarding_case = db.get(
            OnboardingCase,
            onboarding_case_id,
        )

        if onboarding_case is None:
            return

        onboarding_case.completion_percentage = percentage

        if percentage == 0:

            onboarding_case.status = "Not Started"

        elif percentage < 100:

            onboarding_case.status = "In Progress"

        else:

            onboarding_case.status = "Completed"
            onboarding_case.completed_at = datetime.utcnow()

    # ========================================================
    # Document Retrieval
    # ========================================================

    @staticmethod
    def get_documents(
        db: Session,
        onboarding_case_id: int,
    ) -> list[OnboardingDocument]:

        result = db.execute(
            select(OnboardingDocument)
            .where(
                OnboardingDocument.onboarding_case_id
                == onboarding_case_id
            )
            .order_by(OnboardingDocument.id)
        )

        return list(result.scalars().all())

    # ========================================================
    # Document Progress
    # ========================================================

    @staticmethod
    def get_document_progress(
        db: Session,
        onboarding_case_id: int,
    ) -> dict:

        documents = OnboardingService.get_documents(
            db=db,
            onboarding_case_id=onboarding_case_id,
        )

        total_documents = len(documents)

        submitted_documents = sum(
            1
            for document in documents
            if document.status == "Submitted"
        )

        verified_documents = sum(
            1
            for document in documents
            if document.status == "Verified"
        )

        rejected_documents = sum(
            1
            for document in documents
            if document.status == "Rejected"
        )

        pending_documents = sum(
            1
            for document in documents
            if document.status == "Pending"
        )

        completion_percentage = (
            round(
                verified_documents
                / total_documents
                * 100
            )
            if total_documents > 0
            else 0
        )

        return {
            "onboarding_case_id": onboarding_case_id,
            "total_documents": total_documents,
            "submitted_documents": submitted_documents,
            "verified_documents": verified_documents,
            "rejected_documents": rejected_documents,
            "pending_documents": pending_documents,
            "completion_percentage": completion_percentage,
        }

        # ========================================================
    # Overall Onboarding Readiness
    # ========================================================

    @staticmethod
    def get_onboarding_readiness(
        db: Session,
        onboarding_case_id: int,
    ) -> dict:

        onboarding_case = OnboardingService.get_onboarding_case(
            db=db,
            onboarding_case_id=onboarding_case_id,
        )

        if onboarding_case is None:
            return None

        # ----------------------------------------------------
        # Task progress
        # ----------------------------------------------------

        tasks = OnboardingService.get_tasks(
            db=db,
            onboarding_case_id=onboarding_case_id,
        )

        total_tasks = len(tasks)

        completed_tasks = sum(
            1
            for task in tasks
            if task.status == "Completed"
        )

        task_completion_percentage = (
            round(
                completed_tasks
                / total_tasks
                * 100
            )
            if total_tasks > 0
            else 0
        )

        # ----------------------------------------------------
        # Document progress
        # ----------------------------------------------------

        documents = OnboardingService.get_documents(
            db=db,
            onboarding_case_id=onboarding_case_id,
        )

        total_documents = len(documents)

        verified_documents = sum(
            1
            for document in documents
            if document.status == "Verified"
        )

        pending_documents = sum(
            1
            for document in documents
            if document.status == "Pending"
        )

        rejected_documents = sum(
            1
            for document in documents
            if document.status == "Rejected"
        )

        submitted_documents = sum(
            1
            for document in documents
            if document.status == "Submitted"
        )

        document_completion_percentage = (
            round(
                verified_documents
                / total_documents
                * 100
            )
            if total_documents > 0
            else 0
        )

        # ----------------------------------------------------
        # Overall completion
        # ----------------------------------------------------

        overall_completion_percentage = round(
            (
                task_completion_percentage
                + document_completion_percentage
            )
            / 2
        )

        # ----------------------------------------------------
        # Business readiness rule
        # ----------------------------------------------------
        # Employee is ready only when:
        #
        # 1. All tasks are completed
        # 2. All required documents are verified
        #
        # Both conditions must be satisfied.

        onboarding_ready = (
            total_tasks > 0
            and completed_tasks == total_tasks
            and total_documents > 0
            and verified_documents == total_documents
        )

        if onboarding_ready:

            onboarding_status = "Completed"

        elif (
            completed_tasks > 0
            or verified_documents > 0
            or submitted_documents > 0
        ):

            onboarding_status = "In Progress"

        else:

            onboarding_status = "Not Started"

        return {
            "onboarding_case_id": onboarding_case_id,

            "task_completion_percentage":
                task_completion_percentage,

            "document_completion_percentage":
                document_completion_percentage,

            "overall_completion_percentage":
                overall_completion_percentage,

            "total_tasks":
                total_tasks,

            "completed_tasks":
                completed_tasks,

            "total_documents":
                total_documents,

            "verified_documents":
                verified_documents,

            "pending_documents":
                pending_documents,

            "rejected_documents":
                rejected_documents,

            "submitted_documents":
                submitted_documents,

            "onboarding_status":
                onboarding_status,

            "onboarding_ready":
                onboarding_ready,
        }

    # ========================================================
    # Document Upload
    # ========================================================

    @staticmethod
    def submit_document(
        db: Session,
        document_id: int,
        file_name: str,
        file_content: bytes,
    ) -> OnboardingDocument | None:

        document = db.get(
            OnboardingDocument,
            document_id,
        )

        if document is None:
            return None

        if document.status == "Verified":

            raise ValueError(
                "Verified documents cannot be replaced"
            )

        extension = Path(
            file_name
        ).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:

            raise ValueError(
                "Unsupported file type. "
                "Allowed: PDF, PNG, JPG, JPEG"
            )

        if not file_content:

            raise ValueError(
                "Uploaded file is empty"
            )

        if len(file_content) > MAX_FILE_SIZE:

            raise ValueError(
                "File size exceeds the 5 MB limit"
            )

        UPLOAD_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        stored_file_name = (
            f"{document.onboarding_case_id}_"
            f"{document.id}_"
            f"{uuid4().hex}"
            f"{extension}"
        )

        file_path = (
            UPLOAD_DIR
            / stored_file_name
        )

        file_path.write_bytes(
            file_content
        )

        document.file_name = file_name
        document.status = "Submitted"
        document.submitted_at = datetime.utcnow()
        document.verified_at = None

        db.commit()
        db.refresh(document)

        return document

    # ========================================================
    # Document Verification
    # ========================================================

    @staticmethod
    def verify_document(
        db: Session,
        document_id: int,
        status: str,
    ) -> OnboardingDocument | None:

        document = db.get(
            OnboardingDocument,
            document_id,
        )

        if document is None:
            return None

        if status not in {
            "Verified",
            "Rejected",
        }:

            raise ValueError(
                "Status must be Verified or Rejected"
            )

        if document.status != "Submitted":

            raise ValueError(
                "Only submitted documents can be verified"
            )

        document.status = status

        if status == "Verified":

            document.verified_at = datetime.utcnow()

        else:

            document.verified_at = None

        db.commit()
        db.refresh(document)

        return document
