from langgraph.graph import END, START, StateGraph

from app.agents.employee_support.nodes import (
    classify_intent_node,
    hr_policy_node,
    leave_agent_node,
    onboarding_agent_node,
    payroll_agent_node,
    retention_agent_node,
)

from app.agents.employee_support.state import EmployeeSupportState


def route_after_intent(state):
    intent = state.get("intent")

    if intent == "LEAVE":
        return "leave_agent"

    if intent == "HR_POLICY":
        return "hr_policy"

    if intent == "ONBOARDING":
        return "onboarding_agent"

    if intent == "PAYROLL":
        return "payroll_agent"

    if intent == "RETENTION":
        return "retention_agent"

    if intent == "HUMAN_ESCALATION":
        return "human_escalation"

    return "unsupported"

def human_escalation_node(
    state: EmployeeSupportState,
) -> EmployeeSupportState:
    """
    Handle sensitive employment matters that require human review.
    """

    return {
        **state,
        "answer": (
            "This request involves a sensitive employment matter. "
            "Please contact HR for human review and assistance."
        ),
        "sources": [],
        "requires_human": True,
    }


def unsupported_intent_node(
    state: EmployeeSupportState,
) -> EmployeeSupportState:
    """
    Temporary handler for intents whose dedicated agents
    have not yet been implemented.
    """

    intent = state.get("intent", "UNKNOWN")

    return {
        **state,
        "answer": (
            f"The {intent} support capability is not yet available "
            "in this version of OrbitHR. Please contact HR for assistance."
        ),
        "sources": [],
        "requires_human": False,
    }


def build_employee_support_graph():
    graph = StateGraph(EmployeeSupportState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("leave_agent", leave_agent_node)
    graph.add_node("hr_policy", hr_policy_node)
    graph.add_node("onboarding_agent", onboarding_agent_node)
    graph.add_node("human_escalation", human_escalation_node)
    graph.add_node("unsupported", unsupported_intent_node)
    graph.add_node("payroll_agent", payroll_agent_node)
    graph.add_node("retention_agent", retention_agent_node)

    graph.add_edge(START, "classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_after_intent,
        {
            "leave_agent": "leave_agent",
            "hr_policy": "hr_policy",
            "onboarding_agent": "onboarding_agent",
            "human_escalation": "human_escalation",
            "unsupported": "unsupported",
            "payroll_agent": "payroll_agent",
            "retention_agent": "retention_agent",
        },
    )

    graph.add_edge("leave_agent", END)
    graph.add_edge("hr_policy", END)
    graph.add_edge("onboarding_agent", END)
    graph.add_edge("human_escalation", END)
    graph.add_edge("unsupported", END)
    graph.add_edge("payroll_agent", END)
    graph.add_edge("retention_agent", END)

    return graph.compile()


employee_support_graph = build_employee_support_graph()
