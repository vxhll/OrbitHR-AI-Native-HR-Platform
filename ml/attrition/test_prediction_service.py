import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from app.db.database import SessionLocal

from ml.attrition.prediction_service import (
    AttritionPredictionService,
)

def main():

    employee_id = "EMP0001"

    db = SessionLocal()

    try:
        service = AttritionPredictionService()

        result = service.predict(
            db=db,
            employee_id=employee_id,
        )

        print("\n========================================")
        print("ORBIT HR - ATTRITION PREDICTION TEST")
        print("========================================")

        print(f"\nEmployee ID: {result['employee_id']}")

        print("\nPrediction:")
        print(
            f"  Attrition Probability: "
            f"{result['prediction']['attrition_probability_percent']}%"
        )

        print(
            f"  Risk Level: "
            f"{result['prediction']['risk_level']}"
        )

        print(
            f"  Predicted Attrition: "
            f"{result['prediction']['predicted_attrition']}"
        )

        print("\nModel:")
        print(
            f"  Name: "
            f"{result['model']['name']}"
        )

        print(
            f"  Version: "
            f"{result['model']['version']}"
        )

        print("\nFeature Count:")
        print(
            f"  {len(result['features'])} features"
        )

        print("\n========================================")

    finally:
        db.close()


if __name__ == "__main__":
    main()