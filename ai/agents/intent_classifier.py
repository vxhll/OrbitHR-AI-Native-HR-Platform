import sys
from pathlib import Path
from typing import TypedDict

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
# LANGGRAPH
# =========================================================

from langgraph.graph import END, START, StateGraph


# =========================================================
# ORBIT HR AGENTS
# =========================================================

from ai.agents.leave_agent import LeaveAgent
from ai.agents.hr_policy_agent import HRPolicyAgent
from ai.agents.employee_support_agent import EmployeeSupportAgent
from ai.agents.retention_agent import RetentionAgent


# =========================================================
# LANGGRAPH STATE
# =========================================================

class IntentState(TypedDict):
    question: str
    employee_id: str
    intent: str
    answer: str
    sources: list[dict]
    leave_records: list[dict]
    performance_reviews: list[dict]
    engagement_surveys: list[dict]
    retention_assessment: dict


# =========================================================
# INTENT CLASSIFIER
# =========================================================

def classify_intent(
    state: IntentState
) -> IntentState:

    question = state["question"].lower().strip()

    # -----------------------------------------------------
    # RETENTION / ATTRITION
    # -----------------------------------------------------

    if any(
        keyword in question
        for keyword in [
            "attrition",
            "attrition risk",
            "retention risk",
            "flight risk",
            "risk of leaving",
            "likely to leave",
            "turnover risk",
            "retention assessment",
            "retention driver",
            "retention drivers",
            "attrition driver",
            "attrition drivers",
            "retention recommendation",
            "retention recommendations",
            "retention action",
            "retention actions",
            "retain me",
            "how can i be retained",
            "am i at risk of leaving",
            "what is my attrition risk",
            "show my retention assessment",
        ]
    ):

        intent = "RETENTION"


    # -----------------------------------------------------
    # LEAVE
    # -----------------------------------------------------

    elif any(
        keyword in question
        for keyword in [
            "leave",
            "casual leave",
            "sick leave",
            "earned leave",
            "vacation",
            "holiday",
            "leave request",
            "leave balance",
            "leave history",
        ]
    ):

        intent = "LEAVE"


    # -----------------------------------------------------
    # HR POLICY
    # -----------------------------------------------------

    elif any(
        keyword in question
        for keyword in [
            "attendance",
            "working hours",
            "work hours",
            "late",
            "remote work",
            "work from home",
            "wfh",
            "employee handbook",
            "hr policy",
            "policy",
        ]
    ):

        intent = "HR_POLICY"


    # -----------------------------------------------------
    # EMPLOYEE SUPPORT
    # -----------------------------------------------------

    elif any(
        keyword in question
        for keyword in [
            "performance",
            "performance review",
            "rating",
            "manager feedback",
            "promotion",
            "career",
            "feedback",
            "career development",
            "engagement",
            "satisfaction",
            "nps",
            "employee experience",
        ]
    ):

        intent = "EMPLOYEE_SUPPORT"


    # -----------------------------------------------------
    # GENERAL HR
    # -----------------------------------------------------

    else:

        intent = "GENERAL_HR"


    return {
        **state,
        "intent": intent,
    }


# =========================================================
# LEAVE AGENT NODE
# =========================================================

def leave_agent_node(
    state: IntentState
) -> IntentState:

    agent = LeaveAgent()

    result = agent.handle(
        {
            "question": state["question"],
            "employee_id": state["employee_id"],
            "answer": "",
            "sources": [],
            "leave_records": [],
        }
    )

    return {
        **state,
        "answer": result["answer"],
        "sources": result["sources"],
        "leave_records": result["leave_records"],
    }


# =========================================================
# HR POLICY AGENT NODE
# =========================================================

def hr_policy_agent_node(
    state: IntentState
) -> IntentState:

    agent = HRPolicyAgent()

    result = agent.handle(
        {
            "question": state["question"],
            "answer": "",
            "sources": [],
        }
    )

    return {
        **state,
        "answer": result["answer"],
        "sources": result["sources"],
    }


# =========================================================
# EMPLOYEE SUPPORT AGENT NODE
# =========================================================

def employee_support_agent_node(
    state: IntentState
) -> IntentState:

    agent = EmployeeSupportAgent()

    result = agent.handle(
        {
            "question": state["question"],
            "employee_id": state["employee_id"],
            "answer": "",
            "performance_reviews": [],
            "engagement_surveys": [],
        }
    )

    return {
        **state,
        "answer": result["answer"],
        "performance_reviews": result["performance_reviews"],
        "engagement_surveys": result["engagement_surveys"],
    }


# =========================================================
# RETENTION AGENT NODE
# =========================================================

def retention_agent_node(
    state: IntentState
) -> IntentState:

    employee_id = state["employee_id"].strip()

    if not employee_id:

        return {
            **state,
            "answer": (
                "Please provide an employee ID so I can "
                "generate an employee-specific retention "
                "and attrition risk assessment."
            ),
            "retention_assessment": {},
            "sources": [],
        }

    agent = RetentionAgent()

    result = agent.handle(
        employee_id=employee_id
    )

    assessment = result.get(
        "assessment",
        {}
    )

    if result.get("error"):

        return {
            **state,
            "answer": result["error"],
            "retention_assessment": assessment,
            "sources": [],
        }

    prediction = assessment.get(
        "attrition_risk",
        {}
    )

    risk_drivers = assessment.get(
        "risk_drivers",
        []
    )

    retention_actions = assessment.get(
        "retention_actions",
        []
    )

    probability = prediction.get(
        "probability_percent"
    )

    risk_level = prediction.get(
        "risk_level"
    )

    predicted_attrition = prediction.get(
        "predicted_attrition"
    )

    answer_lines = [
        f"Attrition probability: {probability}%",
        f"Risk level: {risk_level}",
        f"Predicted attrition: {predicted_attrition}",
    ]

    if risk_drivers:

        answer_lines.append("")
        answer_lines.append("Risk drivers:")

        for index, driver in enumerate(
            risk_drivers,
            start=1
        ):
            answer_lines.append(
                f"{index}. {driver}"
            )

    if retention_actions:

        answer_lines.append("")
        answer_lines.append("Retention actions:")

        for index, action in enumerate(
            retention_actions,
            start=1
        ):
            answer_lines.append(
                f"{index}. {action}"
            )

    answer_lines.append("")
    answer_lines.append(
        "This assessment is an analytical support signal "
        "and should not be used as an automatic employment decision."
    )

    return {
        **state,
        "answer": "\n".join(answer_lines),
        "retention_assessment": assessment,
        "sources": [],
    }


# =========================================================
# FALLBACK AGENT
# =========================================================

def fallback_agent(
    state: IntentState
) -> IntentState:

    return {
        **state,
        "answer": (
            "I can currently answer questions related to "
            "HR policies, leave, attendance, performance, "
            "engagement, employee support, and retention risk."
        ),
        "sources": [],
    }


# =========================================================
# ROUTE INTENT
# =========================================================

def route_intent(
    state: IntentState
) -> str:

    if state["intent"] == "LEAVE":
        return "leave_agent"

    if state["intent"] == "HR_POLICY":
        return "hr_policy_agent"

    if state["intent"] == "EMPLOYEE_SUPPORT":
        return "employee_support_agent"

    if state["intent"] == "RETENTION":
        return "retention_agent"

    return "fallback_agent"


# =========================================================
# BUILD LANGGRAPH
# =========================================================

def build_intent_graph():

    graph = StateGraph(IntentState)

    # -----------------------------------------------------
    # Nodes
    # -----------------------------------------------------

    graph.add_node(
        "classify_intent",
        classify_intent,
    )

    graph.add_node(
        "leave_agent",
        leave_agent_node,
    )

    graph.add_node(
        "hr_policy_agent",
        hr_policy_agent_node,
    )

    graph.add_node(
        "employee_support_agent",
        employee_support_agent_node,
    )

    graph.add_node(
        "retention_agent",
        retention_agent_node,
    )

    graph.add_node(
        "fallback_agent",
        fallback_agent,
    )

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    graph.add_edge(
        START,
        "classify_intent",
    )

    # -----------------------------------------------------
    # Conditional routing
    # -----------------------------------------------------

    graph.add_conditional_edges(
        "classify_intent",
        route_intent,
        {
            "leave_agent": "leave_agent",
            "hr_policy_agent": "hr_policy_agent",
            "employee_support_agent": "employee_support_agent",
            "retention_agent": "retention_agent",
            "fallback_agent": "fallback_agent",
        },
    )

    # -----------------------------------------------------
    # END
    # -----------------------------------------------------

    graph.add_edge(
        "leave_agent",
        END,
    )

    graph.add_edge(
        "hr_policy_agent",
        END,
    )

    graph.add_edge(
        "employee_support_agent",
        END,
    )

    graph.add_edge(
        "retention_agent",
        END,
    )

    graph.add_edge(
        "fallback_agent",
        END,
    )

    return graph.compile()


# =========================================================
# CLI TEST
# =========================================================

if __name__ == "__main__":

    app = build_intent_graph()

    print()
    print("OrbitHR Multi-Agent Workflow")
    print("----------------------------")

    employee_id = input(
        "\nEnter employee ID "
        "(leave blank for general/policy question): "
    ).strip()

    question = input(
        "\nEnter employee question: "
    ).strip()

    result = app.invoke(
        {
            "question": question,
            "employee_id": employee_id,
            "intent": "",
            "answer": "",
            "sources": [],
            "leave_records": [],
            "performance_reviews": [],
            "engagement_surveys": [],
            "retention_assessment": {},
        }
    )

    print()
    print("Question:")
    print(result["question"])

    print()
    print("Employee ID:")
    print(
        result["employee_id"]
        if result["employee_id"]
        else "Not provided"
    )

    print()
    print("Detected Intent:")
    print(result["intent"])

    print()
    print("Answer:")
    print(result["answer"])

    # -----------------------------------------------------
    # Leave history
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Retention assessment
    # -----------------------------------------------------

    if result["retention_assessment"]:

        assessment = result[
            "retention_assessment"
        ]

        print()
        print("Retention Assessment:")
        print("---------------------")

        employee = assessment.get(
            "employee",
            {}
        )

        if employee:

            print(
                f"Employee: "
                f"{employee.get('name', 'N/A')}"
            )

            print(
                f"Employee ID: "
                f"{assessment.get('employee_id', 'N/A')}"
            )

        attrition_risk = assessment.get(
            "attrition_risk",
            {}
        )

        if attrition_risk:

            print()
            print("Attrition Risk:")

            print(
                f"Probability: "
                f"{attrition_risk.get('probability_percent')}%"
            )

            print(
                f"Risk Level: "
                f"{attrition_risk.get('risk_level')}"
            )

            print(
                f"Predicted Attrition: "
                f"{attrition_risk.get('predicted_attrition')}"
            )

        risk_drivers = assessment.get(
            "risk_drivers",
            []
        )

        if risk_drivers:

            print()
            print("Risk Drivers:")

            for index, driver in enumerate(
                risk_drivers,
                start=1
            ):
                print(
                    f"{index}. {driver}"
                )

        retention_actions = assessment.get(
            "retention_actions",
            []
        )

        if retention_actions:

            print()
            print("Retention Actions:")

            for index, action in enumerate(
                retention_actions,
                start=1
            ):
                print(
                    f"{index}. {action}"
                )

    # -----------------------------------------------------
    # Sources
    # -----------------------------------------------------

    if result["sources"]:

        print()
        print("Sources:")

        for source in result["sources"]:

            print(
                f"- {source['source']} "
                f"(distance: {source['distance']})"
            )