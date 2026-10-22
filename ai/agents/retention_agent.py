import sys
from pathlib import Path
from typing import TypedDict
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"

# Keep the project-level ML services ahead of backend packages.
for directory in (BACKEND_DIR, PROJECT_ROOT):
    directory_string = str(directory)
    if directory_string in sys.path:
        sys.path.remove(directory_string)

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(1, str(BACKEND_DIR))


# ---------------------------------------------------------
# Backend models / database
# ---------------------------------------------------------

from app.db.database import SessionLocal
from app.models.employee import Employee
from app.models.performance_review import PerformanceReview
from app.models.engagement_survey import EngagementSurvey


# ---------------------------------------------------------
# ML prediction service
# ---------------------------------------------------------

from ml.attrition.prediction_service import (
    AttritionPredictionService,
)


# ---------------------------------------------------------
# Agent State
# ---------------------------------------------------------

class RetentionAgentState(TypedDict, total=False):
    employee_id: str
    employee: dict
    prediction: dict
    features: dict
    risk_drivers: list[str]
    retention_actions: list[str]
    assessment: dict
    error: str


# ---------------------------------------------------------
# Retention Agent
# ---------------------------------------------------------

class RetentionAgent:

    def __init__(self):

        self.prediction_service = (
            AttritionPredictionService()
        )

    # -----------------------------------------------------
    # Check performance data availability
    # -----------------------------------------------------

    def has_performance_data(
        self,
        db: Session,
        employee_id: str,
    ) -> bool:

        record = db.scalar(
            select(PerformanceReview.id)
            .where(
                PerformanceReview.employee_id == employee_id
            )
            .limit(1)
        )

        return record is not None

    # -----------------------------------------------------
    # Check engagement data availability
    # -----------------------------------------------------

    def has_engagement_data(
        self,
        db: Session,
        employee_id: str,
    ) -> bool:

        record = db.scalar(
            select(EngagementSurvey.id)
            .where(
                EngagementSurvey.employee_id == employee_id
            )
            .limit(1)
        )

        return record is not None

    # -----------------------------------------------------
    # Get employee profile
    # -----------------------------------------------------

    def get_employee(
        self,
        db: Session,
        employee_id: str,
    ):

        employee = db.scalar(
            select(Employee).where(
                Employee.employee_id == employee_id
            )
        )

        return employee

    # -----------------------------------------------------
    # Identify risk drivers
    # -----------------------------------------------------

    def identify_risk_drivers(
        self,
        features: dict,
        performance_data_available: bool,
        engagement_data_available: bool,
    ) -> list[str]:

        drivers = []

        # -------------------------------------------------
        # Engagement
        # -------------------------------------------------

        if engagement_data_available:

            engagement = features.get(
                "average_engagement_score",
                0,
            )

            if engagement < 6:

                drivers.append(
                    f"Low engagement score ({engagement:.2f}/10)"
                )

            elif engagement < 7:

                drivers.append(
                    f"Moderate engagement score ({engagement:.2f}/10)"
                )

        else:

            drivers.append(
                "No engagement survey data available"
            )

        # -------------------------------------------------
        # Job satisfaction
        # -------------------------------------------------

        if engagement_data_available:

            satisfaction = features.get(
                "average_job_satisfaction_score",
                0,
            )

            if satisfaction < 6:

                drivers.append(
                    f"Low job satisfaction ({satisfaction:.2f}/10)"
                )

            elif satisfaction < 7:

                drivers.append(
                    f"Moderate job satisfaction ({satisfaction:.2f}/10)"
                )

        # -------------------------------------------------
        # Performance
        # -------------------------------------------------

        if performance_data_available:

            performance = features.get(
                "average_performance_rating",
                0,
            )

            if performance < 2.5:

                drivers.append(
                    f"Low performance rating ({performance:.2f}/5)"
                )

            elif performance < 3:

                drivers.append(
                    f"Moderate performance rating ({performance:.2f}/5)"
                )

        else:

            drivers.append(
                "No performance review data available"
            )

        # -------------------------------------------------
        # Manager feedback
        # -------------------------------------------------

        if performance_data_available:

            manager_feedback = features.get(
                "average_manager_feedback_score",
                0,
            )

            if manager_feedback < 5:

                drivers.append(
                    f"Low manager feedback score ({manager_feedback:.2f}/10)"
                )

            elif manager_feedback < 6:

                drivers.append(
                    f"Moderate manager feedback score ({manager_feedback:.2f}/10)"
                )

        # -------------------------------------------------
        # Attendance
        # -------------------------------------------------

        attendance_count = features.get(
            "attendance_record_count",
            0,
        )

        absent_days = features.get(
            "absent_days",
            0,
        )

        if attendance_count > 0:

            if absent_days >= 10:

                drivers.append(
                    f"High absence count ({absent_days} days)"
                )

            elif absent_days >= 5:

                drivers.append(
                    f"Elevated absence count ({absent_days} days)"
                )

        # -------------------------------------------------
        # Working hours
        # -------------------------------------------------

        if attendance_count > 0:

            average_hours = features.get(
                "average_hours_worked",
                0,
            )

            if average_hours < 7:

                drivers.append(
                    f"Low average working hours ({average_hours:.2f})"
                )

        # -------------------------------------------------
        # Leave
        # -------------------------------------------------

        leave_days = features.get(
            "total_leave_days",
            0,
        )

        if leave_days >= 20:

            drivers.append(
                f"High leave usage ({leave_days} days)"
            )

        elif leave_days >= 15:

            drivers.append(
                f"Elevated leave usage ({leave_days} days)"
            )

        # -------------------------------------------------
        # Career progression
        # -------------------------------------------------

        promotion_count = features.get(
            "promotion_count",
            0,
        )

        tenure = features.get(
            "tenure_years",
            0,
        )

        if tenure >= 2 and promotion_count == 0:

            drivers.append(
                "No recorded promotion despite tenure"
            )

        # -------------------------------------------------
        # Fallback
        # -------------------------------------------------

        if not drivers:

            drivers.append(
                "No major risk signal identified from the available workforce data"
            )

        return drivers

    # -----------------------------------------------------
    # Generate retention actions
    # -----------------------------------------------------

    def generate_retention_actions(
        self,
        features: dict,
        risk_level: str,
        performance_data_available: bool,
        engagement_data_available: bool,
    ) -> list[str]:

        actions = []

        # -------------------------------------------------
        # Engagement
        # -------------------------------------------------

        if engagement_data_available:

            engagement = features.get(
                "average_engagement_score",
                0,
            )

            if engagement < 7:

                actions.append(
                    "Schedule an employee-manager engagement check-in."
                )

        # -------------------------------------------------
        # Job satisfaction
        # -------------------------------------------------

        if engagement_data_available:

            satisfaction = features.get(
                "average_job_satisfaction_score",
                0,
            )

            if satisfaction < 7:

                actions.append(
                    "Discuss job satisfaction, workload, and role expectations."
                )

        # -------------------------------------------------
        # Performance
        # -------------------------------------------------

        if performance_data_available:

            performance = features.get(
                "average_performance_rating",
                0,
            )

            if performance < 3:

                actions.append(
                    "Review performance goals and provide targeted coaching support."
                )

        else:

            actions.append(
                "Consider scheduling a performance review to establish a baseline."
            )

        # -------------------------------------------------
        # Manager feedback
        # -------------------------------------------------

        if performance_data_available:

            manager_feedback = features.get(
                "average_manager_feedback_score",
                0,
            )

            if manager_feedback < 6:

                actions.append(
                    "Review manager feedback and establish a structured feedback cadence."
                )

        # -------------------------------------------------
        # Attendance
        # -------------------------------------------------

        absent_days = features.get(
            "absent_days",
            0,
        )

        if absent_days >= 5:

            actions.append(
                "Review attendance patterns and identify potential workload or support needs."
            )

        # -------------------------------------------------
        # Career progression
        # -------------------------------------------------

        promotion_count = features.get(
            "promotion_count",
            0,
        )

        tenure = features.get(
            "tenure_years",
            0,
        )

        if tenure >= 2 and promotion_count == 0:

            actions.append(
                "Discuss career-development and progression opportunities."
            )

        # -------------------------------------------------
        # Risk-based human review
        # -------------------------------------------------

        if risk_level == "High":

            actions.append(
                "Prioritize a human HR review of the employee's situation."
            )

        elif risk_level == "Medium":

            actions.append(
                "Schedule a proactive HR or manager follow-up."
            )

        # -------------------------------------------------
        # Default
        # -------------------------------------------------

        if not actions:

            actions.append(
                "Continue regular manager check-ins and engagement practices."
            )

        return actions

    # -----------------------------------------------------
    # Build assessment
    # -----------------------------------------------------

    def build_assessment(
        self,
        employee_id: str,
        employee,
        prediction: dict,
        features: dict,
        performance_data_available: bool,
        engagement_data_available: bool,
    ) -> dict:

        risk_level = prediction["risk_level"]

        risk_drivers = self.identify_risk_drivers(
            features=features,
            performance_data_available=performance_data_available,
            engagement_data_available=engagement_data_available,
        )

        retention_actions = self.generate_retention_actions(
            features=features,
            risk_level=risk_level,
            performance_data_available=performance_data_available,
            engagement_data_available=engagement_data_available,
        )

        return {
            "employee_id": employee_id,

            "employee": {
                "name": employee.full_name,
                "department_id": employee.department_id,
                "job_role": employee.job_role,
                "job_level": employee.job_level,
                "work_location": employee.work_location,
            },

            "attrition_risk": {
                "probability_percent": prediction[
                    "attrition_probability_percent"
                ],
                "risk_level": risk_level,
                "predicted_attrition": prediction[
                    "predicted_attrition"
                ],
            },

            "risk_drivers": risk_drivers,

            "retention_actions": retention_actions,

            "model": {
                "name": "Logistic Regression",
                "version": "baseline-1.0",
            },

            "note": (
                "This assessment is an analytical support signal "
                "and should not be used as an automatic employment decision."
            ),
        }

    # -----------------------------------------------------
    # Main agent handler
    # -----------------------------------------------------

    def handle(
        self,
        employee_id: str,
    ) -> RetentionAgentState:

        db = SessionLocal()

        try:

            employee = self.get_employee(
                db=db,
                employee_id=employee_id,
            )

            if employee is None:

                return {
                    "employee_id": employee_id,
                    "error": (
                        f"Employee {employee_id} not found"
                    ),
                }

            # ---------------------------------------------
            # Generate ML prediction
            # ---------------------------------------------

            prediction_result = (
                self.prediction_service.predict(
                    db=db,
                    employee_id=employee_id,
                )
            )

            # ---------------------------------------------
            # Check actual data availability
            # ---------------------------------------------

            performance_data_available = (
                self.has_performance_data(
                    db=db,
                    employee_id=employee_id,
                )
            )

            engagement_data_available = (
                self.has_engagement_data(
                    db=db,
                    employee_id=employee_id,
                )
            )

            prediction = prediction_result[
                "prediction"
            ]

            features = prediction_result[
                "features"
            ]

            # ---------------------------------------------
            # Build assessment
            # ---------------------------------------------

            assessment = self.build_assessment(
                employee_id=employee_id,
                employee=employee,
                prediction=prediction,
                features=features,
                performance_data_available=(
                    performance_data_available
                ),
                engagement_data_available=(
                    engagement_data_available
                ),
            )

            return {
                "employee_id": employee_id,
                "employee": assessment["employee"],
                "prediction": prediction,
                "features": features,
                "risk_drivers": assessment[
                    "risk_drivers"
                ],
                "retention_actions": assessment[
                    "retention_actions"
                ],
                "assessment": assessment,
            }

        except Exception as exc:

            return {
                "employee_id": employee_id,
                "error": str(exc),
            }

        finally:

            db.close()


    # -----------------------------------------------------
    # Event-based v3 synthetic retention assessment
    # -----------------------------------------------------

    def handle_v3(
        self,
        employee_id: str,
        prediction_date: date,
    ) -> RetentionAgentState:
        """Generate a retention assessment from synthetic v3 data only."""

        from datetime import date as Date
        from ml.attrition.event_based_prediction_service import (
            EventBasedPredictionService,
        )

        if not isinstance(prediction_date, Date):
            return {
                "employee_id": employee_id,
                "error": "prediction_date must be a datetime.date value.",
            }

        try:
            service = EventBasedPredictionService()
            result = service.predict(
                employee_id=employee_id,
                prediction_date=prediction_date,
            )

            prediction = result["prediction"]
            features = result["features"]
            explanation = result["explanation"]

            feature_labels = {
                "absent_days_90d": "Absence days in the last 90 days",
                "average_employee_nps_90d": "Employee NPS in the last 90 days",
                "promotion_count_90d": "Promotion count in the last 90 days",
                "total_leave_days_90d": "Leave days in the last 90 days",
                "average_job_satisfaction_score_90d": "Job satisfaction score",
                "tenure_years": "Employee tenure",
                "age": "Age",
                "average_manager_feedback_score_90d": "Manager feedback score",
                "average_performance_rating_90d": "Performance rating",
                "average_hours_worked_90d": "Average hours worked",
            }

            risk_drivers = []

            for item in (
                explanation.get("top_positive_drivers", [])
            ):
                feature = item["feature"]
                risk_drivers.append({
                    "feature": feature,
                    "label": feature_labels.get(
                        feature,
                        feature.replace("_", " ").capitalize(),
                    ),
                    "value": item["value"],
                    "direction": "increases",
                    "contribution_log_odds": item[
                        "contribution_log_odds"
                    ],
                    "interpretation": (
                        "Associated with a higher model score; "
                        "not evidence of causation."
                    ),
                })

            for item in (
                explanation.get("top_negative_drivers", [])
            ):
                feature = item["feature"]
                risk_drivers.append({
                    "feature": feature,
                    "label": feature_labels.get(
                        feature,
                        feature.replace("_", " ").capitalize(),
                    ),
                    "value": item["value"],
                    "direction": "decreases",
                    "contribution_log_odds": item[
                        "contribution_log_odds"
                    ],
                    "interpretation": (
                        "Associated with a lower model score; "
                        "not evidence of causation."
                    ),
                })

            risk_level = prediction["risk_level"]
            retention_actions = []

            if risk_level in ("High", "Medium"):
                if features.get("absent_days_90d", 0) > 0:
                    retention_actions.append(
                        "Offer a confidential check-in to understand "
                        "whether workplace support or flexibility is needed."
                    )

                if features.get("average_employee_nps_90d", 0) < 0:
                    retention_actions.append(
                        "Invite voluntary feedback and review team-level "
                        "concerns with an HR partner."
                    )

                if features.get(
                    "average_job_satisfaction_score_90d", 0
                ) < 3:
                    retention_actions.append(
                        "Discuss role satisfaction, growth opportunities, "
                        "and development goals with the employee."
                    )

                if features.get(
                    "average_manager_feedback_score_90d", 0
                ) < 3:
                    retention_actions.append(
                        "Offer a supportive manager conversation and "
                        "review coaching or communication needs."
                    )

                retention_actions.append(
                    "Have HR review the signals with appropriate context "
                    "before deciding whether any follow-up is warranted."
                )
            else:
                retention_actions.append(
                    "Continue regular employee check-ins and "
                    "monitor workforce-level trends."
                )

            if not retention_actions:
                retention_actions.append(
                    "Offer a voluntary check-in to understand the "
                    "employee's current needs and goals."
                )

            assessment = {
                "employee_id": employee_id,
                "prediction_date": result["prediction_date"],
                "employee": {
                    "employee_id": employee_id,
                    "department": features.get("department"),
                    "age": features.get("age"),
                    "job_level": features.get("job_level"),
                    "tenure_years": features.get("tenure_years"),
                    "annual_base_salary_inr": features.get(
                        "annual_base_salary_inr"
                    ),
                    "data_source": "synthetic_v3",
                },
                "attrition_risk": prediction,
                "risk_drivers": risk_drivers,
                "retention_actions": retention_actions,
                "model": result["model"],
                "outcome_horizon_days": prediction[
                    "outcome_horizon_days"
                ],
                "research_notice": result["research_notice"],
                "note": (
                    "Synthetic research assessment only. Model drivers "
                    "are associations, not causes. This output is not "
                    "validated for real employees and must not be used "
                    "as an automatic employment decision."
                ),
            }

            return {
                "employee_id": employee_id,
                "prediction_date": result["prediction_date"],
                "data_source": "synthetic_v3",
                "employee": assessment["employee"],
                "prediction": prediction,
                "features": features,
                "risk_drivers": risk_drivers,
                "retention_actions": retention_actions,
                "assessment": assessment,
                "model": result["model"],
                "research_notice": result["research_notice"],
            }

        except (ValueError, FileNotFoundError) as exc:
            return {
                "employee_id": employee_id,
                "prediction_date": prediction_date.isoformat(),
                "data_source": "synthetic_v3",
                "error": str(exc),
            }
        except Exception:
            return {
                "employee_id": employee_id,
                "prediction_date": prediction_date.isoformat(),
                "data_source": "synthetic_v3",
                "error": (
                    "The synthetic v3 retention assessment failed. "
                    "Check the backend logs for details."
                ),
            }


# ---------------------------------------------------------
# CLI Test
# ---------------------------------------------------------

def main():

    employee_id = "EMP0137"

    agent = RetentionAgent()

    result = agent.handle(
        employee_id=employee_id
    )

    print("\n========================================")
    print("ORBIT HR - RETENTION AGENT")
    print("========================================")

    if "error" in result:

        print(
            f"\nError: {result['error']}"
        )

        return

    prediction = result["prediction"]

    print(
        f"\nEmployee: "
        f"{result['employee']['name']}"
    )

    print(
        f"Employee ID: "
        f"{result['employee_id']}"
    )

    print("\nAttrition Risk")
    print("----------------")

    print(
        f"Probability: "
        f"{prediction['attrition_probability_percent']}%"
    )

    print(
        f"Risk Level: "
        f"{prediction['risk_level']}"
    )

    print(
        f"Predicted Attrition: "
        f"{prediction['predicted_attrition']}"
    )

    print("\nRisk Drivers")
    print("----------------")

    for index, driver in enumerate(
        result["risk_drivers"],
        start=1,
    ):

        print(
            f"{index}. {driver}"
        )

    print("\nRetention Actions")
    print("----------------")

    for index, action in enumerate(
        result["retention_actions"],
        start=1,
    ):

        print(
            f"{index}. {action}"
        )

    print("\n========================================")
    print(
        "Assessment completed successfully."
    )
    print("========================================")


if __name__ == "__main__":
    main()