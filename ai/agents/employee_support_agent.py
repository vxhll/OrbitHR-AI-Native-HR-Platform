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
# ORBIT HR MODELS
# =========================================================

from app.models.employee import Employee
from app.models.performance_review import PerformanceReview
from app.models.engagement_survey import EngagementSurvey


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
# DATABASE
# =========================================================

engine = create_engine(
    DATABASE_URL
)


# =========================================================
# AGENT STATE
# =========================================================

class EmployeeSupportState(TypedDict):
    question: str
    employee_id: str
    answer: str
    performance_reviews: list[dict]
    engagement_surveys: list[dict]


# =========================================================
# EMPLOYEE SUPPORT AGENT
# =========================================================

class EmployeeSupportAgent:

    # =====================================================
    # GET EMPLOYEE PROFILE
    # =====================================================

    def get_employee(
        self,
        employee_id: str
    ):

        with Session(engine) as db:

            return db.scalar(
                select(Employee)
                .where(
                    Employee.employee_id == employee_id
                )
            )


    # =====================================================
    # GET PERFORMANCE REVIEWS
    # =====================================================

    def get_performance_reviews(
        self,
        employee_id: str
    ) -> list[dict]:

        with Session(engine) as db:

            records = db.scalars(
                select(PerformanceReview)
                .where(
                    PerformanceReview.employee_id
                    == employee_id
                )
                .order_by(
                    PerformanceReview.review_period.desc()
                )
            ).all()

            return [
                {
                    "review_period": (
                        record.review_period
                        if isinstance(
                            record.review_period,
                            str
                        )
                        else record.review_period.isoformat()
                    ),
                    "performance_rating":
                        record.performance_rating_1to5,
                    "manager_feedback_score":
                        record.manager_feedback_score_1to10,
                    "promotion_flag":
                        record.promotion_flag,
                }
                for record in records
            ]


    # =====================================================
    # GET ENGAGEMENT SURVEYS
    # =====================================================

    def get_engagement_surveys(
        self,
        employee_id: str
    ) -> list[dict]:

        with Session(engine) as db:

            records = db.scalars(
                select(EngagementSurvey)
                .where(
                    EngagementSurvey.employee_id
                    == employee_id
                )
                .order_by(
                    EngagementSurvey.survey_period.desc()
                )
            ).all()

            return [
                {
                    "survey_period": (
                        record.survey_period
                        if isinstance(
                            record.survey_period,
                            str
                        )
                        else record.survey_period.isoformat()
                    ),
                    "engagement_score":
                        record.engagement_score_1to10,
                    "job_satisfaction_score":
                        record.job_satisfaction_score_1to10,
                    "employee_nps":
                        record.employee_nps,
                }
                for record in records
            ]


    # =====================================================
    # GENERATE PERFORMANCE SUMMARY
    # =====================================================

    def generate_performance_summary(
        self,
        employee_id: str,
        reviews: list[dict]
    ) -> str:

        if not reviews:

            return (
                f"No performance review records were "
                f"found for employee {employee_id}."
            )

        ratings = [
            review["performance_rating"]
            for review in reviews
            if review["performance_rating"] is not None
        ]

        feedback_scores = [
            review["manager_feedback_score"]
            for review in reviews
            if review["manager_feedback_score"] is not None
        ]

        promotions = sum(
            1
            for review in reviews
            if review["promotion_flag"]
        )

        average_rating = (
            sum(ratings) / len(ratings)
            if ratings
            else 0
        )

        average_feedback = (
            sum(feedback_scores) / len(feedback_scores)
            if feedback_scores
            else 0
        )

        lines = [
            f"Employee {employee_id} Performance Summary",
            "",
            f"Total reviews: {len(reviews)}",
            f"Average performance rating: "
            f"{average_rating:.2f}/5",
            f"Average manager feedback score: "
            f"{average_feedback:.2f}/10",
            f"Promotion records: {promotions}",
            "",
            "Review history:",
        ]

        for review in reviews:

            promotion = (
                "Yes"
                if review["promotion_flag"]
                else "No"
            )

            lines.append(
                f"- {review['review_period']} | "
                f"Rating: {review['performance_rating']}/5 | "
                f"Manager feedback: "
                f"{review['manager_feedback_score']}/10 | "
                f"Promotion: {promotion}"
            )

        return "\n".join(lines)


    # =====================================================
    # GENERATE ENGAGEMENT SUMMARY
    # =====================================================

    def generate_engagement_summary(
        self,
        employee_id: str,
        surveys: list[dict]
    ) -> str:

        if not surveys:

            return (
                f"No engagement survey records were "
                f"found for employee {employee_id}."
            )

        engagement_scores = [
            survey["engagement_score"]
            for survey in surveys
            if survey["engagement_score"] is not None
        ]

        satisfaction_scores = [
            survey["job_satisfaction_score"]
            for survey in surveys
            if survey["job_satisfaction_score"] is not None
        ]

        nps_scores = [
            survey["employee_nps"]
            for survey in surveys
            if survey["employee_nps"] is not None
        ]

        average_engagement = (
            sum(engagement_scores)
            / len(engagement_scores)
            if engagement_scores
            else 0
        )

        average_satisfaction = (
            sum(satisfaction_scores)
            / len(satisfaction_scores)
            if satisfaction_scores
            else 0
        )

        average_nps = (
            sum(nps_scores)
            / len(nps_scores)
            if nps_scores
            else 0
        )

        return (
            f"Employee {employee_id} Engagement Summary\n\n"
            f"Survey records: {len(surveys)}\n"
            f"Average engagement score: "
            f"{average_engagement:.2f}/10\n"
            f"Average job satisfaction: "
            f"{average_satisfaction:.2f}/10\n"
            f"Average employee NPS: "
            f"{average_nps:.2f}"
        )


    # =====================================================
    # HANDLE REQUEST
    # =====================================================

    def handle(
        self,
        state: EmployeeSupportState
    ) -> EmployeeSupportState:

        employee_id = state["employee_id"].strip()

        if not employee_id:

            return {
                **state,
                "answer": (
                    "Please provide an employee ID for "
                    "employee-specific performance and "
                    "engagement information."
                ),
                "performance_reviews": [],
                "engagement_surveys": [],
            }

        employee = self.get_employee(
            employee_id
        )

        if not employee:

            return {
                **state,
                "answer": (
                    f"Employee {employee_id} "
                    f"was not found."
                ),
                "performance_reviews": [],
                "engagement_surveys": [],
            }

        reviews = self.get_performance_reviews(
            employee_id
        )

        surveys = self.get_engagement_surveys(
            employee_id
        )

        question = state["question"].lower()

        wants_performance = any(
            keyword in question
            for keyword in [
                "performance",
                "performance review",
                "rating",
                "manager feedback",
                "promotion",
            ]
        )

        wants_engagement = any(
            keyword in question
            for keyword in [
                "engagement",
                "satisfaction",
                "nps",
                "employee experience",
            ]
        )

        # -------------------------------------------------
        # Performance only
        # -------------------------------------------------

        if wants_performance and not wants_engagement:

            answer = self.generate_performance_summary(
                employee_id,
                reviews
            )

        # -------------------------------------------------
        # Engagement only
        # -------------------------------------------------

        elif wants_engagement and not wants_performance:

            answer = self.generate_engagement_summary(
                employee_id,
                surveys
            )

        # -------------------------------------------------
        # Both performance and engagement
        # -------------------------------------------------

        elif wants_performance and wants_engagement:

            performance_summary = (
                self.generate_performance_summary(
                    employee_id,
                    reviews
                )
            )

            engagement_summary = (
                self.generate_engagement_summary(
                    employee_id,
                    surveys
                )
            )

            answer = (
                performance_summary
                + "\n\n"
                + engagement_summary
            )

        # -------------------------------------------------
        # General employee-support question
        # -------------------------------------------------

        else:

            performance_summary = (
                self.generate_performance_summary(
                    employee_id,
                    reviews
                )
            )

            engagement_summary = (
                self.generate_engagement_summary(
                    employee_id,
                    surveys
                )
            )

            answer = (
                performance_summary
                + "\n\n"
                + engagement_summary
            )

        return {
            **state,
            "answer": answer,
            "performance_reviews": reviews,
            "engagement_surveys": surveys,
        }


# =========================================================
# CLI TEST
# =========================================================

if __name__ == "__main__":

    print()
    print("OrbitHR Employee Support Agent")
    print("------------------------------")

    employee_id = input(
        "\nEnter employee ID: "
    ).strip()

    question = input(
        "\nEnter employee support question: "
    ).strip()

    agent = EmployeeSupportAgent()

    result = agent.handle(
        {
            "question": question,
            "employee_id": employee_id,
            "answer": "",
            "performance_reviews": [],
            "engagement_surveys": [],
        }
    )

    print()
    print("Answer:")
    print(result["answer"])