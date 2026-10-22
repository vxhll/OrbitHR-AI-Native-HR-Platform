import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from app.db.database import SessionLocal
from app.models.employee import Employee
from sqlalchemy import select

from ml.attrition.prediction_service import (
    AttritionPredictionService,
)


def main():

    db = SessionLocal()

    try:

        service = AttritionPredictionService()

        employees = db.scalars(
            select(Employee)
        ).all()

        results = []

        for employee in employees:

            result = service.predict(
                db=db,
                employee_id=employee.employee_id,
            )

            prediction = result["prediction"]

            results.append(
                (
                    employee.employee_id,
                    employee.full_name,
                    prediction[
                        "attrition_probability_percent"
                    ],
                    prediction["risk_level"],
                )
            )

        results.sort(
            key=lambda item: item[2],
            reverse=True,
        )

        print("\n========================================")
        print("ORBIT HR - TOP ATTRITION RISK EMPLOYEES")
        print("========================================")

        for index, result in enumerate(
            results[:10],
            start=1,
        ):

            employee_id = result[0]
            name = result[1]
            probability = result[2]
            risk_level = result[3]

            print(
                f"{index}. "
                f"{employee_id} | "
                f"{name} | "
                f"{probability}% | "
                f"{risk_level}"
            )

        print("\n========================================")

    finally:

        db.close()


if __name__ == "__main__":
    main()