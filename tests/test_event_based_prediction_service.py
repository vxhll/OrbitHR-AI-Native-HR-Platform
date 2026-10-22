import math
from datetime import date
import pandas as pd
import pytest

from ml.attrition.event_based_feature_service import FEATURES
from ml.attrition.event_based_prediction_service import (
    EventBasedPredictionService,
)


class FakePipeline:
    """Return a controlled probability without loading the real model."""

    def __init__(self, probability):
        self.probability = probability

    def predict_proba(self, data):
        return [[1.0 - self.probability, self.probability]]


def make_feature_payload():
    """Create a complete, valid 17-feature payload."""
    values = {
        "age": 30,
        "tenure_years": 2.5,
        "job_level": 2,
        "annual_base_salary_inr": 600000,
        "attendance_record_count_90d": 65,
        "average_hours_worked_90d": 8.0,
        "absent_days_90d": 2,
        "average_performance_rating_90d": 3.5,
        "average_manager_feedback_score_90d": 7.0,
        "promotion_count_90d": 0,
        "average_engagement_score_90d": 7.0,
        "average_job_satisfaction_score_90d": 7.0,
        "average_employee_nps_90d": 1.0,
        "leave_record_count_90d": 1,
        "total_leave_days_90d": 2,
        "payroll_record_count_90d": 3,
        "department": "Engineering",
    }

    return {feature: values[feature] for feature in FEATURES}


@pytest.mark.parametrize(
    ("probability", "expected_risk", "expected_prediction"),
    [
        (0.75, "High", True),
        (0.50, "Medium", False),
        (0.20, "Low", False),
    ],
)
def test_predict_returns_probability_and_risk(
    monkeypatch,
    probability,
    expected_risk,
    expected_prediction,
):
    service = EventBasedPredictionService()

    artifact = {
        "pipeline": FakePipeline(probability),
        "threshold": 0.55,
        "features": FEATURES,
        "version": "event-based-v3",
        "target": "attrition",
    }

    monkeypatch.setattr(
        service,
        "_load_artifact",
        lambda: artifact,
    )

    monkeypatch.setattr(
        service,
        "build_features",
        lambda employee_id, prediction_date: make_feature_payload(),
    )

    # Isolate prediction/risk tests from the real model explanation.
    monkeypatch.setattr(
        service,
        "explain_prediction",
        lambda feature_data, artifact: {
            "method": "test explanation",
            "baseline_log_odds": 0.0,
            "reconstructed_log_odds": 0.0,
            "reference": "Test-only explanation.",
            "top_positive_drivers": [],
            "top_negative_drivers": [],
            "contributions": [],
        },
    )

    result = service.predict(
        employee_id="EMP0001",
        prediction_date=date(2025, 12, 1),
    )

    assert result["employee_id"] == "EMP0001"

    assert result["prediction"]["attrition_probability_percent"] == (
        probability * 100
    )

    assert result["prediction"]["risk_level"] == expected_risk

    assert (
        result["prediction"]["predicted_attrition"]
        is expected_prediction
    )

    assert result["model"]["version"] == "event-based-v3"
    assert result["data_source"] == "synthetic_v3"
    assert len(result["features"]) == 17

    assert result["explanation"]["method"] == "test explanation"


def test_unsupported_employee_date_is_rejected(monkeypatch):
    service = EventBasedPredictionService()

    monkeypatch.setattr(
        service,
        "_load_eligible_snapshots",
        lambda: {("EMP0001", date(2025, 12, 1))},
    )

    with pytest.raises(
        ValueError,
        match="Unsupported employee/date",
    ):
        service.build_features(
            employee_id="EMP0001",
            prediction_date=date(2026, 6, 30),
        )

def test_real_model_explanation_reconstructs_log_odds():
    service = EventBasedPredictionService()

    prediction_date = date(2025, 12, 1)
    employee_id = "EMP0001"

    artifact = service._load_artifact()
    feature_data = service.build_features(
        employee_id=employee_id,
        prediction_date=prediction_date,
    )

    explanation = service.explain_prediction(
        feature_data=feature_data,
        artifact=artifact,
    )

    model_features = pd.DataFrame(
        [[feature_data[name] for name in artifact["features"]]],
        columns=artifact["features"],
    )

    actual_log_odds = float(
        artifact["pipeline"].decision_function(model_features)[0]
    )

    assert len(explanation["contributions"]) == 22

    assert math.isclose(
        explanation["reconstructed_log_odds"],
        actual_log_odds,
        abs_tol=1e-5,
    )

    assert len(explanation["top_positive_drivers"]) <= 5
    assert len(explanation["top_negative_drivers"]) <= 5

    for item in explanation["contributions"]:
        assert item["direction"] in {
            "increases",
            "decreases",
            "neutral",
        }

def test_build_features_rejects_non_date_input(monkeypatch):
    service = EventBasedPredictionService()

    with pytest.raises(TypeError, match="prediction_date must be a date"):
        service.build_features(
            employee_id="EMP0001",
            prediction_date="2025-12-01",
        )


def test_unknown_employee_is_rejected(monkeypatch):
    service = EventBasedPredictionService()

    monkeypatch.setattr(
        service,
        "_load_eligible_snapshots",
        lambda: {("EMP0001", date(2025, 12, 1))},
    )

    with pytest.raises(ValueError, match="Unsupported employee/date"):
        service.build_features(
            employee_id="EMP9999",
            prediction_date=date(2025, 12, 1),
        )


@pytest.mark.parametrize(
    ("employee_id", "prediction_date"),
    [
        ("EMP0001", date(2025, 9, 1)),
        ("EMP0001", date(2025, 12, 1)),
        ("EMP0002", date(2025, 10, 1)),
        ("EMP0002", date(2025, 12, 1)),
        ("EMP0003", date(2025, 11, 1)),
    ],
)
def test_real_model_predictions_for_supported_employee_dates(
    employee_id,
    prediction_date,
):
    service = EventBasedPredictionService()
    result = service.predict(
        employee_id=employee_id,
        prediction_date=prediction_date,
    )

    probability = result["prediction"]["attrition_probability_percent"]
    risk_level = result["prediction"]["risk_level"]

    assert result["employee_id"] == employee_id
    assert result["prediction_date"] == prediction_date.isoformat()
    assert 0.0 <= probability <= 100.0
    assert risk_level in {"Low", "Medium", "High"}
    assert result["model"]["version"] == "event-based-v3"
    assert result["data_source"] == "synthetic_v3"
    assert len(result["features"]) == 17
    assert len(result["explanation"]["contributions"]) == 22


def test_real_model_prediction_is_deterministic():
    service = EventBasedPredictionService()

    first = service.predict(
        employee_id="EMP0001",
        prediction_date=date(2025, 12, 1),
    )
    second = service.predict(
        employee_id="EMP0001",
        prediction_date=date(2025, 12, 1),
    )

    assert (
        first["prediction"]["attrition_probability_percent"]
        == second["prediction"]["attrition_probability_percent"]
    )
    assert (
        first["prediction"]["risk_level"]
        == second["prediction"]["risk_level"]
    )
    assert (
        first["prediction"]["predicted_attrition"]
        == second["prediction"]["predicted_attrition"]
    )
    assert (
        first["explanation"]["reconstructed_log_odds"]
        == second["explanation"]["reconstructed_log_odds"]
    )
