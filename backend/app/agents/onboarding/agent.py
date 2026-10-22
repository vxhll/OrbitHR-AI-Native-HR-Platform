
from datetime import date

from sqlalchemy.orm import Session

from app.models.department import Department
from app.services.onboarding_service import OnboardingService


class OnboardingAgent:
    """
    Read-only onboarding assistant.

    Provides onboarding status and explainable, rule-based
    recommendations using existing onboarding data.
    It does not complete tasks or verify documents.
    """

    def __init__(self):
        self.service = OnboardingService()

    def get_status(
        self,
        db: Session,
        onboarding_case_id: int,
    ) -> dict:
        readiness = self.service.get_onboarding_readiness(
            db,
            onboarding_case_id,
        )

        if readiness is None:
            return {
                "answer": "The onboarding case could not be found.",
                "sources": [],
                "requires_human": False,
            }

        return {
            "answer": self._format_readiness(readiness),
            "sources": [
                {
                    "type": "onboarding_case",
                    "onboarding_case_id": onboarding_case_id,
                }
            ],
            "requires_human": False,
        }

    def get_recommendations(
        self,
        db: Session,
        onboarding_case_id: int,
    ) -> dict:
        readiness = self.service.get_onboarding_readiness(
            db,
            onboarding_case_id,
        )

        if readiness is None:
            return {
                "onboarding_case_id": onboarding_case_id,
                "status": "Not Found",
                "overall_completion_percentage": 0,
                "onboarding_ready": False,
                "recommendations": [],
                "requires_human": False,
                "sources": [],
            }

        tasks = self.service.get_tasks(
            db=db,
            onboarding_case_id=onboarding_case_id,
        )

        documents = self.service.get_documents(
            db=db,
            onboarding_case_id=onboarding_case_id,
        )

        onboarding_case = self.service.get_onboarding_case(
            db=db,
            onboarding_case_id=onboarding_case_id,
        )

        employee = (
            self.service.get_employee(
                db=db,
                employee_id=onboarding_case.employee_id,
            )
            if onboarding_case is not None
            else None
        )

        today = date.today()
        recommendations = []

        # Recommend pending tasks, with required overdue tasks first.
        pending_tasks = [
            task
            for task in tasks
            if task.status != "Completed"
        ]

        pending_tasks.sort(
            key=lambda task: (
                task.due_date is None,
                task.due_date or date.max,
                task.id,
            )
        )

        for task in pending_tasks:
            overdue = (
                task.due_date is not None
                and task.due_date < today
            )

            if overdue and task.required:
                priority = "High"
                reason = "This required task is overdue."
            elif overdue:
                priority = "Medium"
                reason = "This task is overdue."
            elif task.required:
                priority = "Medium"
                reason = "Complete this task by its due date."
            else:
                priority = "Low"
                reason = "Consider completing this task."

            recommendations.append({
                "category": "task",
                "priority": priority,
                "title": task.title,
                "reason": reason,
                "task_id": task.id,
                "due_date": (
                    task.due_date.isoformat()
                    if task.due_date is not None
                    else None
                ),
            })

        # Recommend document actions based on current document status.
        for document in documents:
            if document.status == "Verified":
                continue

            if document.status == "Rejected":
                priority = "High"
                reason = (
                    "This document was rejected. Contact HR if the "
                    "reason for rejection is unclear, then submit "
                    "a corrected document."
                )
            elif document.status == "Submitted":
                priority = "Medium"
                reason = (
                    "This document is awaiting HR verification. "
                    "No further action is needed unless HR requests changes."
                )
            else:
                priority = "Medium"
                reason = "Submit this required onboarding document."

            recommendations.append({
                "category": "document",
                "priority": priority,
                "title": document.document_type,
                "reason": reason,
                "document_id": document.id,
                "document_status": document.status,
            })

        # Add role-specific guidance using the employee's actual department.
        if employee is not None:
            department = db.get(
                Department,
                employee.department_id,
            )

            role_text = str(employee.job_role or "").lower()
            department_text = str(
                department.name if department is not None else ""
            ).lower()

            is_technical_role = any(
                keyword in role_text
                for keyword in (
                    "engineer",
                    "developer",
                    "technical",
                )
            )

            is_engineering_department = (
                "engineering" in department_text
            )

            if is_technical_role or is_engineering_department:
                recommendations.append({
                    "category": "role_guidance",
                    "priority": "Low",
                    "title": "Prepare your technical environment",
                    "reason": (
                        "For technical roles, confirm your required tools, "
                        "repository access, and development environment "
                        "with your manager or IT team."
                    ),
                })

        # Provide a neutral status recommendation if no actions remain.
        if not recommendations:
            recommendations.append({
                "category": "status",
                "priority": "Low",
                "title": "No outstanding onboarding actions",
                "reason": (
                    "No pending tasks or unverified documents were found."
                ),
            })

        priority_order = {
            "High": 0,
            "Medium": 1,
            "Low": 2,
        }

        recommendations.sort(
            key=lambda item: priority_order.get(
                item["priority"],
                3,
            )
        )

        # Human review is required when a submitted document awaits HR.
        requires_human = any(
            document.status == "Submitted"
            for document in documents
        )

        return {
            "onboarding_case_id": onboarding_case_id,
            "status": readiness["onboarding_status"],
            "overall_completion_percentage": (
                readiness["overall_completion_percentage"]
            ),
            "onboarding_ready": readiness["onboarding_ready"],
            "recommendations": recommendations,
            "requires_human": requires_human,
            "sources": [
                {
                    "type": "onboarding_case",
                    "onboarding_case_id": onboarding_case_id,
                }
            ],
        }

    @staticmethod
    def _format_readiness(readiness: dict) -> str:
        return (
            f"Your onboarding is currently "
            f"{readiness['onboarding_status']}. "
            f"Overall completion is "
            f"{readiness['overall_completion_percentage']}%. "
            f"Tasks completed: "
            f"{readiness['completed_tasks']}/"
            f"{readiness['total_tasks']}. "
            f"Documents verified: "
            f"{readiness['verified_documents']}/"
            f"{readiness['total_documents']}. "
            f"Onboarding ready: "
            f"{'Yes' if readiness['onboarding_ready'] else 'No'}."
        )
