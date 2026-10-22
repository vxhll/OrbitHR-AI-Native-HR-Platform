from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy.orm import Session

from ml.attrition.feature_service import (
    FEATURE_COLUMNS,
    build_attrition_features,
)


class AttritionPredictionService:
    """
    Shared service for loading the attrition model,
    building employee features, and generating predictions.
    """

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]

        self.model_path = (
            self.project_root
            / "ml"
            / "attrition"
            / "attrition_logistic_regression.joblib"
        )

        self.model = None

    def load_model(self):
        """Load the trained attrition model once."""

        if self.model is None:

            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"Attrition model not found: {self.model_path}"
                )

            self.model = joblib.load(self.model_path)

        return self.model

    def predict(
        self,
        db: Session,
        employee_id: str,
    ) -> dict:

        # Build the exact same features used during training.
        feature_data = build_attrition_features(
            db=db,
            employee_id=employee_id,
        )

        # Create model input in the expected column order.
        features = pd.DataFrame(
            [
                [
                    feature_data[column]
                    for column in FEATURE_COLUMNS
                ]
            ],
            columns=FEATURE_COLUMNS,
        )

        # Load trained model.
        model = self.load_model()

        # Prediction.
        prediction = int(
            model.predict(features)[0]
        )

        # Probability of attrition.
        probability = float(
            model.predict_proba(features)[0][1]
        )

        probability_percent = round(
            probability * 100,
            2,
        )

        # Demo risk classification.
        if probability >= 0.70:
            risk_level = "High"

        elif probability >= 0.40:
            risk_level = "Medium"

        else:
            risk_level = "Low"

        return {
            "employee_id": employee_id,

            "prediction": {
                "attrition_probability_percent": probability_percent,
                "risk_level": risk_level,
                "predicted_attrition": bool(prediction),
            },

            "model": {
                "name": "Logistic Regression",
                "version": "baseline-1.0",
            },

            "features": feature_data,
        }