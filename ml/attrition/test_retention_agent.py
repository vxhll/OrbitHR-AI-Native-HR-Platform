import sys
from pathlib import Path

from dotenv import load_dotenv


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
ENV_FILE = BACKEND_DIR / ".env"


# ---------------------------------------------------------
# Load backend environment
# ---------------------------------------------------------

load_dotenv(ENV_FILE)


# ---------------------------------------------------------
# Python import paths
# ---------------------------------------------------------

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------
# Retention Agent
# ---------------------------------------------------------

from ai.agents.retention_agent import RetentionAgent


def main():

    employee_id = "EMP0137"

    agent = RetentionAgent()

    result = agent.handle(
        employee_id=employee_id
    )

    print("\n========================================")
    print("ORBIT HR - RETENTION AGENT TEST")
    print("========================================")

    if "error" in result:

        print(
            f"\nError: {result['error']}"
        )

        return

    employee = result["employee"]
    prediction = result["prediction"]

    print(
        f"\nEmployee: "
        f"{employee['name']}"
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


if __name__ == "__main__":
    main()