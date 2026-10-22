from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from ml.attrition.event_based_feature_service import (
    FEATURES,
    MODEL_VERSION,
    validate_feature_payload,
)


class EventBasedPredictionService:
    """
    Synthetic-data prototype for the OrbitHR event-based v3 model.

    Uses the validated synthetic employee, event, and snapshot files.
    Does not query the operational HR database.
    """

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[2]

        self.model_path = (
            self.project_root
            / "ml"
            / "attrition"
            / "attrition_event_based_logistic_regression.joblib"
        )

        self.employees_path = (
            self.project_root
            / "data"
            / "synthetic_v3"
            / "employees.csv"
        )

        self.events_path = (
            self.project_root
            / "data"
            / "synthetic_v3"
            / "hr_events.csv"
        )

        self.snapshots_path = (
            self.project_root
            / "data"
            / "synthetic_v3"
            / "temporal_attrition_snapshots.csv"
        )

        self._artifact: dict[str, Any] | None = None
        self._employees: pd.DataFrame | None = None
        self._events: pd.DataFrame | None = None
        self._eligible_snapshots: set[tuple[str, date]] | None = None

    def _load_artifact(self) -> dict[str, Any]:
        if self._artifact is None:
            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"V3 model artifact not found: {self.model_path}"
                )

            artifact = joblib.load(self.model_path)

            required_keys = {
                "pipeline",
                "threshold",
                "features",
                "version",
                "target",
            }

            if not isinstance(artifact, dict):
                raise ValueError(
                    "V3 model artifact must be a dictionary."
                )

            missing = required_keys - set(artifact)

            if missing:
                raise ValueError(
                    f"V3 model artifact is missing keys: {sorted(missing)}"
                )

            if artifact["version"] != MODEL_VERSION:
                raise ValueError(
                    f"Unexpected model version: {artifact['version']!r}"
                )

            if artifact["features"] != FEATURES:
                raise ValueError(
                    "Saved model feature schema does not match "
                    "the v3 feature service."
                )

            threshold = float(artifact["threshold"])

            if not 0.0 <= threshold <= 1.0:
                raise ValueError(
                    "Model classification threshold must be between 0 and 1."
                )

            self._artifact = artifact

        return self._artifact

    def _load_source_data(
        self,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        if self._employees is None:
            if not self.employees_path.exists():
                raise FileNotFoundError(
                    f"Synthetic employee file not found: "
                    f"{self.employees_path}"
                )

            employees = pd.read_csv(
                self.employees_path,
                parse_dates=["hire_date"],
            )

            required_employee_columns = {
                "employee_id",
                "hire_date",
                "age",
                "department",
                "job_level",
                "annual_base_salary_inr",
            }

            missing = required_employee_columns - set(employees.columns)

            if missing:
                raise ValueError(
                    "Synthetic employee data is missing columns: "
                    f"{sorted(missing)}"
                )

            if employees["employee_id"].duplicated().any():
                raise ValueError(
                    "Duplicate employee IDs found in synthetic data."
                )

            self._employees = employees.set_index(
                "employee_id",
                drop=False,
            )

        if self._events is None:
            if not self.events_path.exists():
                raise FileNotFoundError(
                    f"Synthetic HR event file not found: {self.events_path}"
                )

            events = pd.read_csv(
                self.events_path,
                parse_dates=["event_date"],
            )

            required_event_columns = {
                "employee_id",
                "event_date",
                "event_type",
                "value",
            }

            missing = required_event_columns - set(events.columns)

            if missing:
                raise ValueError(
                    "Synthetic HR events are missing columns: "
                    f"{sorted(missing)}"
                )

            if events[
                ["employee_id", "event_date", "event_type", "value"]
            ].isna().any().any():
                raise ValueError(
                    "Synthetic HR events contain missing required values."
                )

            self._events = events

        return self._employees, self._events

    def _load_eligible_snapshots(self) -> set[tuple[str, date]]:
        """
        Load supported employee/date combinations only.

        Target labels are deliberately excluded from the columns read.
        """
        if self._eligible_snapshots is None:
            if not self.snapshots_path.exists():
                raise FileNotFoundError(
                    f"Validated snapshot dataset not found: "
                    f"{self.snapshots_path}"
                )

            snapshots = pd.read_csv(
                self.snapshots_path,
                usecols=["employee_id", "prediction_date"],
                parse_dates=["prediction_date"],
            )

            self._eligible_snapshots = {
                (
                    str(row.employee_id),
                    row.prediction_date.date(),
                )
                for row in snapshots.itertuples(index=False)
            }

        return self._eligible_snapshots

    @staticmethod
    def _mean_or_default(
        history: pd.DataFrame,
        event_type: str,
        default: float,
    ) -> float:
        values = history.loc[
            history["event_type"] == event_type,
            "value",
        ]

        if values.empty:
            return default

        return float(values.mean())

    @staticmethod
    def _count(
        history: pd.DataFrame,
        event_type: str,
    ) -> int:
        return int((history["event_type"] == event_type).sum())

    def build_features(
        self,
        employee_id: str,
        prediction_date: date,
    ) -> dict[str, Any]:
        if not isinstance(prediction_date, date):
            raise TypeError("prediction_date must be a date.")

        cutoff_date = prediction_date

        if (
            employee_id,
            cutoff_date,
        ) not in self._load_eligible_snapshots():
            raise ValueError(
                "Unsupported employee/date combination. This synthetic "
                "prototype only supports employee/date combinations "
                "present in the validated v3 snapshots."
            )

        cutoff = pd.Timestamp(cutoff_date).normalize()
        window_start = cutoff - pd.Timedelta(days=90)

        employees, events = self._load_source_data()

        if employee_id not in employees.index:
            raise ValueError(
                f"Synthetic employee {employee_id} was not found."
            )

        employee = employees.loc[employee_id]
        hire_date = pd.Timestamp(employee["hire_date"]).normalize()

        if hire_date >= cutoff:
            raise ValueError(
                "Employee must have been hired before the prediction date."
            )

        employee_events = events.loc[
            events["employee_id"] == employee_id
        ]

        # Include the start date and exclude the prediction date.
        history = employee_events.loc[
            (employee_events["event_date"] >= window_start)
            & (employee_events["event_date"] < cutoff)
        ]

        tenure_years = max(
            0.0,
            (cutoff - hire_date).days / 365.25,
        )

        feature_data = {
            "age": int(employee["age"]),
            "tenure_years": round(tenure_years, 3),
            "job_level": int(employee["job_level"]),
            "annual_base_salary_inr": int(
                employee["annual_base_salary_inr"]
            ),
            "attendance_record_count_90d": self._count(
                history, "attendance_absent"
            ),
            "average_hours_worked_90d": round(
                self._mean_or_default(
                    history, "hours_worked", 8.0
                ),
                3,
            ),
            "absent_days_90d": int(
                history.loc[
                    history["event_type"] == "attendance_absent",
                    "value",
                ].sum()
            ),
            "average_performance_rating_90d": round(
                self._mean_or_default(
                    history, "performance_rating", 3.5
                ),
                3,
            ),
            "average_manager_feedback_score_90d": round(
                self._mean_or_default(
                    history, "manager_feedback_score", 3.5
                ),
                3,
            ),
            "promotion_count_90d": self._count(
                history, "promotion"
            ),
            "average_engagement_score_90d": round(
                self._mean_or_default(
                    history, "engagement_score", 3.5
                ),
                3,
            ),
            "average_job_satisfaction_score_90d": round(
                self._mean_or_default(
                    history, "job_satisfaction_score", 3.5
                ),
                3,
            ),
            "average_employee_nps_90d": round(
                self._mean_or_default(
                    history, "employee_nps", 0.0
                ),
                3,
            ),
            "leave_record_count_90d": self._count(
                history, "leave_start"
            ),
            "total_leave_days_90d": self._count(
                history, "leave_day"
            ),
            "payroll_record_count_90d": self._count(
                history, "payroll_paid"
            ),
            "department": str(employee["department"]),
        }

        return validate_feature_payload(feature_data)

    def explain_prediction(
        self,
        feature_data: dict[str, Any],
        artifact: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Decompose the logistic regression score into feature contributions.

        Contributions are additive terms in transformed model space.
        They explain the model score, not causation.
        """
        pipeline = artifact["pipeline"]
        preprocessing = pipeline.named_steps["preprocessing"]
        classifier = pipeline.named_steps["classifier"]

        model_features = pd.DataFrame(
            [[feature_data[name] for name in artifact["features"]]],
            columns=artifact["features"],
        )

        transformed = preprocessing.transform(model_features)
        feature_names = preprocessing.get_feature_names_out()
        coefficients = classifier.coef_[0]

        if transformed.shape[1] != len(coefficients):
            raise ValueError(
                "Transformed feature count does not match model coefficients."
            )

        if len(feature_names) != len(coefficients):
            raise ValueError(
                "Transformed feature names do not match model coefficients."
            )

        if hasattr(transformed, "toarray"):
            transformed_values = transformed.toarray()[0].tolist()
        else:
            transformed_values = transformed[0].tolist()

        contributions = [
            float(value) * float(coefficient)
            for value, coefficient in zip(
                transformed_values,
                coefficients,
            )
        ]

        items = []

        for name, transformed_value, contribution in zip(
            feature_names,
            transformed_values,
            contributions,
        ):
            if name.startswith("numeric__"):
                source_name = name.removeprefix("numeric__")
                original_value = feature_data[source_name]

            elif name.startswith("categorical__department_"):
                source_name = "department"
                original_value = feature_data["department"]

            else:
                source_name = name
                original_value = None

            score = float(contribution)

            items.append(
                {
                    "feature": source_name,
                    "transformed_feature": name,
                    "value": original_value,
                    "transformed_value": round(
                        float(transformed_value), 6
                    ),
                    "contribution_log_odds": round(score, 6),
                    "direction": (
                        "increases"
                        if score > 0
                        else "decreases"
                        if score < 0
                        else "neutral"
                    ),
                }
            )

        items.sort(
            key=lambda item: abs(item["contribution_log_odds"]),
            reverse=True,
        )

        positive = sorted(
            (
                item for item in items
                if item["contribution_log_odds"] > 0
            ),
            key=lambda item: item["contribution_log_odds"],
            reverse=True,
        )

        negative = sorted(
            (
                item for item in items
                if item["contribution_log_odds"] < 0
            ),
            key=lambda item: item["contribution_log_odds"],
        )

        baseline_log_odds = float(classifier.intercept_[0])
        reconstructed_log_odds = (
            baseline_log_odds + sum(contributions)
        )

        return {
            "method": (
                "Logistic regression contribution decomposition"
            ),
            "baseline_log_odds": round(baseline_log_odds, 6),
            "reconstructed_log_odds": round(
                reconstructed_log_odds, 6
            ),
            "reference": (
                "Contributions are additive terms in transformed model "
                "space. They explain the model score, not causation, and "
                "are not percentage-point changes in attrition probability."
            ),
            "top_positive_drivers": positive[:5],
            "top_negative_drivers": negative[:5],
            "contributions": items,
        }

    def predict(
        self,
        employee_id: str,
        prediction_date: date,
    ) -> dict[str, Any]:
        artifact = self._load_artifact()

        feature_data = self.build_features(
            employee_id=employee_id,
            prediction_date=prediction_date,
        )

        model_features = pd.DataFrame(
            [[feature_data[name] for name in artifact["features"]]],
            columns=artifact["features"],
        )

        pipeline = artifact["pipeline"]

        probability = float(
            pipeline.predict_proba(model_features)[0][1]
        )

        threshold = float(artifact["threshold"])
        predicted_attrition = probability >= threshold

        # Display risk bands; binary classification uses the saved threshold.
        if probability >= 0.70:
            risk_level = "High"
        elif probability >= 0.40:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        explanation = self.explain_prediction(
            feature_data=feature_data,
            artifact=artifact,
        )

        return {
            "employee_id": employee_id,
            "prediction_date": prediction_date.isoformat(),
            "prediction": {
                "attrition_probability_percent": round(
                    probability * 100, 2
                ),
                "risk_level": risk_level,
                "predicted_attrition": bool(predicted_attrition),
                "classification_threshold": threshold,
                "outcome_horizon_days": 180,
            },
            "model": {
                "name": "Logistic Regression",
                "version": artifact["version"],
            },
            "data_source": "synthetic_v3",
            "research_notice": (
                "Synthetic-data prototype only. This prediction is not "
                "validated for real employees and must not independently "
                "determine employment decisions."
            ),
            "features": feature_data,
            "explanation": explanation,
        }
