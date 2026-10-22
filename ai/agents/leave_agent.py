import os
import sys
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# =========================================================
# ORBIT HR IMPORTS
# =========================================================

from ai.rag.services.rag_service import RAGService
from app.models.leave_record import LeaveRecord


# =========================================================
# ENVIRONMENT
# =========================================================

ENV_PATH = BACKEND_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured in backend/.env"
    )


# =========================================================
# DATABASE ENGINE
# =========================================================

engine = create_engine(
    DATABASE_URL
)


# =========================================================
# LEAVE AGENT STATE
# =========================================================

class LeaveAgentState(TypedDict):
    question: str
    employee_id: str
    answer: str
    sources: list[dict]
    leave_records: list[dict]


# =========================================================
# LEAVE AGENT
# =========================================================

class LeaveAgent:

    def __init__(self):

        self.rag_service = RAGService()


    # =====================================================
    # DETERMINE WHETHER QUESTION IS A POLICY QUESTION
    # =====================================================

    def is_policy_question(
        self,
        question: str
    ) -> bool:

        question_lower = question.lower().strip()

        policy_keywords = [
    # General policy terms
    "policy",
    "policies",
    "rule",
    "rules",
    "allowed",
    "eligible",
    "eligibility",
    "entitled",
    "entitlement",

    # Quantity / limits
    "how many",
    "how much",
    "how long",
    "leave days",
    "leave limit",
    "leave allowance",
    "leave quota",
    "leave entitlement",

    # Common policy questions
    "can an employee",
    "can employee",
    "can i take",
    "can i use",
    "can we take",
    "what can i take",
    "what leave can",
    "what type of leave",
    "which leave",
    "which leaves",
    "how can employee take",
    "how can an employee take",
    "how can i take",
    "how do i take",
    "how does leave",
    "how to take leave",
    "what is the leave",
    "what are the leave",

    # Leave types
    "casual leave",
    "sick leave",
    "earned leave",
    "annual leave",
    "vacation",
    "holiday",
]

        return any(
            keyword in question_lower
            for keyword in policy_keywords
        )


    # =====================================================
    # ANSWER HR POLICY QUESTION USING RAG
    # =====================================================

    def answer_policy_question(
        self,
        question: str
    ) -> dict:

        return self.rag_service.ask(
            question=question,
            top_k=3
        )


    # =====================================================
    # GET EMPLOYEE LEAVE HISTORY
    # =====================================================

    def get_leave_history(
        self,
        employee_id: str
    ) -> list[dict]:

        with Session(engine) as db:

            records = db.scalars(
                select(LeaveRecord)
                .where(
                    LeaveRecord.employee_id == employee_id
                )
                .order_by(
                    LeaveRecord.start_date.desc()
                )
            ).all()

            return [
                {
                    "leave_type": record.leave_type,
                    "start_date": record.start_date.isoformat(),
                    "end_date": record.end_date.isoformat(),
                    "days": record.days,
                    "approval_status": record.approval_status,
                }
                for record in records
            ]


    # =====================================================
    # GENERATE EMPLOYEE LEAVE SUMMARY
    # =====================================================

    def generate_leave_summary(
        self,
        employee_id: str,
        records: list[dict]
    ) -> str:

        if not records:

            return (
                f"No leave records were found for employee "
                f"{employee_id}."
            )


        # -------------------------------------------------
        # Total leave days
        # -------------------------------------------------

        total_days = sum(
            record["days"]
            for record in records
        )


        # -------------------------------------------------
        # Leave type summary
        # -------------------------------------------------

        leave_type_summary = {}

        for record in records:

            leave_type = record["leave_type"]

            leave_type_summary[leave_type] = (
                leave_type_summary.get(
                    leave_type,
                    0
                )
                + record["days"]
            )


        # -------------------------------------------------
        # Approval status summary
        # -------------------------------------------------

        status_summary = {}

        for record in records:

            status = record["approval_status"]

            status_summary[status] = (
                status_summary.get(
                    status,
                    0
                )
                + 1
            )


        # -------------------------------------------------
        # Build response
        # -------------------------------------------------

        lines = [

            f"Employee {employee_id} Leave Summary",

            "",

            f"Total leave records: {len(records)}",

            f"Total leave days: {total_days}",

            "",

            "By leave type:",
        ]


        for leave_type, days in leave_type_summary.items():

            lines.append(
                f"- {leave_type}: {days} day(s)"
            )


        lines.extend(
            [
                "",
                "Approval status:",
            ]
        )


        for status, count in status_summary.items():

            lines.append(
                f"- {status}: {count}"
            )


        return "\n".join(lines)


    # =====================================================
    # HANDLE LEAVE REQUEST
    # =====================================================

    def handle(
        self,
        state: LeaveAgentState
    ) -> LeaveAgentState:

        question = state["question"]

        employee_id = state.get(
            "employee_id",
            ""
        ).strip()


        # =================================================
        # PATH 1 — POLICY QUESTION
        # =================================================

        if self.is_policy_question(question):

            result = self.answer_policy_question(
                question
            )

            return {
                **state,

                "answer": result["answer"],

                "sources": result["sources"],

                "leave_records": [],
            }


        # =================================================
        # PATH 2 — EMPLOYEE-SPECIFIC QUESTION
        # =================================================

        if employee_id:

            leave_records = self.get_leave_history(
                employee_id
            )

            answer = self.generate_leave_summary(
                employee_id,
                leave_records
            )

            return {
                **state,

                "answer": answer,

                "sources": [],

                "leave_records": leave_records,
            }


        # =================================================
        # PATH 3 — EMPLOYEE ID REQUIRED
        # =================================================

        return {
            **state,

            "answer": (
                "Please provide an employee ID for "
                "employee-specific leave information."
            ),

            "sources": [],

            "leave_records": [],
        }


# =========================================================
# CLI TEST
# =========================================================

if __name__ == "__main__":

    print()
    print("OrbitHR Leave Agent")
    print("-------------------")


    # -----------------------------------------------------
    # Employee ID
    # -----------------------------------------------------

    employee_id = input(
        "\nEnter employee ID "
        "(leave blank for policy question): "
    ).strip()


    # -----------------------------------------------------
    # Question
    # -----------------------------------------------------

    question = input(
        "\nEnter leave-related question: "
    ).strip()


    # -----------------------------------------------------
    # Create Agent
    # -----------------------------------------------------

    agent = LeaveAgent()


    # -----------------------------------------------------
    # Execute Agent
    # -----------------------------------------------------

    result = agent.handle(
        {
            "question": question,

            "employee_id": employee_id,

            "answer": "",

            "sources": [],

            "leave_records": [],
        }
    )


    # =====================================================
    # ANSWER
    # =====================================================

    print()
    print("Answer:")
    print(result["answer"])


    # =====================================================
    # EMPLOYEE LEAVE HISTORY
    # =====================================================

    if result["leave_records"]:

        print()
        print("Leave History:")
        print("-------------")


        for record in result["leave_records"]:

            print(
                f"{record['leave_type']} | "
                f"{record['start_date']} → "
                f"{record['end_date']} | "
                f"{record['days']} day(s) | "
                f"{record['approval_status']}"
            )


    # =====================================================
    # RAG SOURCES
    # =====================================================

    if result["sources"]:

        print()
        print("Sources:")


        for source in result["sources"]:

            print(
                f"- {source['source']} "
                f"(distance: {source['distance']})"
            )