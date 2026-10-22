from datetime import date

from ai.agents.retention_agent import RetentionAgent

from app.agents.employee_support.state import EmployeeSupportState
from app.agents.leave.agent import LeaveAgent
from app.agents.onboarding.agent import OnboardingAgent
from app.agents.payroll.agent import PayrollAgent
from app.db.database import SessionLocal
from app.services.rag.answer_service import HRPolicyAnswerService
from app.services.support.intent_classifier import IntentClassifier


def classify_intent_node(
    state: EmployeeSupportState,
) -> EmployeeSupportState:
    """Classify the employee's question and update graph state."""

    classifier = IntentClassifier()
    result = classifier.classify(state["question"])

    return {
        **state,
        "intent": result["intent"],
        "confidence": result["confidence"],
        "intent_reason": result["reason"],
    }


def hr_policy_node(
    state: EmployeeSupportState,
) -> EmployeeSupportState:
    """Answer HR policy questions using the existing RAG knowledge base."""

    service = HRPolicyAnswerService()
    result = service.answer_question(
        question=state["question"],
        top_k=5,
    )

    return {
        **state,
        "answer": result["answer"],
        "sources": result["sources"],
        "requires_human": False,
    }


def leave_agent_node(
    state: EmployeeSupportState,
) -> EmployeeSupportState:
    """Handle leave-related employee questions."""

    agent = LeaveAgent()
    result = agent.answer(state["question"])

    return {
        **state,
        "answer": result["answer"],
        "sources": result["sources"],
        "requires_human": result["requires_human"],
    }


def onboarding_agent_node(
    state: EmployeeSupportState,
) -> EmployeeSupportState:
    """Handle onboarding questions using live PostgreSQL data."""

    onboarding_case_id = state.get("onboarding_case_id")

    if onboarding_case_id is None:
        return {
            **state,
            "answer": (
                "I could not determine your active onboarding case. "
                "Please contact HR for assistance."
            ),
            "sources": [],
            "requires_human": True,
        }

    db = SessionLocal()

    try:
        agent = OnboardingAgent()
        result = agent.get_status(db, onboarding_case_id)

        return {
            **state,
            "answer": result["answer"],
            "sources": result["sources"],
            "requires_human": result["requires_human"],
        }
    finally:
        db.close()


def payroll_agent_node(
    state: EmployeeSupportState,
) -> EmployeeSupportState:
    """Handle payroll-related employee questions."""

    employee_id = state.get("employee_id")

    if not employee_id:
        return {
            **state,
            "answer": (
                "I could not determine your employee ID. "
                "Please contact HR for payroll assistance."
            ),
            "sources": [],
            "requires_human": True,
        }

    db = SessionLocal()

    try:
        agent = PayrollAgent()
        result = agent.get_latest_payroll(
            db=db,
            employee_id=employee_id,
        )

        return {
            **state,
            "answer": result["answer"],
            "sources": result["sources"],
            "requires_human": result["requires_human"],
        }
    finally:
        db.close()


def retention_agent_node(
    state: EmployeeSupportState,
) -> EmployeeSupportState:
    """Handle synthetic v3 retention assessments with human-review safeguards."""

    employee_id = state.get("employee_id")
    prediction_date_value = state.get("prediction_date")

    if not employee_id:
        return {
            **state,
            "answer": (
                "A synthetic employee ID is required for this retention "
                "research assessment. Please verify the input or contact "
                "HR for assistance."
            ),
            "sources": [],
            "requires_human": True,
            "error": "Missing synthetic employee ID.",
        }

    if not prediction_date_value:
        return {
            **state,
            "answer": (
                "A prediction date is required for this retention research "
                "assessment. Supported dates must exist in the validated "
                "synthetic v3 snapshots. Please verify the date or contact "
                "HR for assistance."
            ),
            "sources": [],
            "requires_human": True,
            "error": "Missing prediction date.",
        }

    try:
        if isinstance(prediction_date_value, date):
            parsed_date = prediction_date_value
        else:
            parsed_date = date.fromisoformat(prediction_date_value)
    except (TypeError, ValueError):
        return {
            **state,
            "answer": (
                "The prediction date must use YYYY-MM-DD format, "
                "for example 2025-12-01. Please verify the input "
                "or contact HR for assistance."
            ),
            "sources": [],
            "requires_human": True,
            "error": "Invalid prediction date format.",
        }

    try:
        agent = RetentionAgent()
        result = agent.handle_v3(
            employee_id=employee_id,
            prediction_date=parsed_date,
        )
    except Exception as exc:
        # Keep assessment failures visible and require human review.
        return {
            **state,
            "answer": (
                "The synthetic retention assessment could not be "
                "completed because of an internal processing error. "
                "Please contact HR for review."
            ),
            "sources": [],
            "requires_human": True,
            "error": str(exc),
        }

    if result.get("error"):
        return {
            **state,
            "answer": (
                "The synthetic retention assessment could not be "
                f"completed: {result['error']} "
                "Please verify the employee/date combination or "
                "contact HR for review."
            ),
            "sources": [],
            "requires_human": True,
            "error": result["error"],
        }

    prediction = result["prediction"]

    driver_lines = [
        f"- {driver['label']}: {driver['direction']} the model score"
        for driver in result["risk_drivers"][:5]
    ]

    action_lines = [
        f"- {action}"
        for action in result["retention_actions"]
    ]

    answer = (
        "Synthetic Retention Research Assessment\n\n"
        f"Employee ID: {employee_id}\n"
        f"Prediction date: {result['prediction_date']}\n"
        f"Model: {result['model']['version']}\n"
        "Estimated attrition probability: "
        f"{prediction['attrition_probability_percent']}%\n"
        f"Risk band: {prediction['risk_level']}\n"
        "Outcome horizon: "
        f"{prediction['outcome_horizon_days']} days\n\n"
        "Model-associated drivers:\n"
        + (
            "\n".join(driver_lines)
            if driver_lines
            else "- No model-associated drivers returned."
        )
        + "\n\nSupportive follow-up options:\n"
        + (
            "\n".join(action_lines)
            if action_lines
            else "- Request an HR review before deciding on follow-up."
        )
        + "\n\nResearch limitation: "
        + result["research_notice"]
    )

    return {
        **state,
        "answer": answer,
        "sources": [],
        "requires_human": True,
    }
