from datetime import date, timedelta

import pytest

from ml.attrition.event_based_feature_service import (
    FEATURES,
    LOOKBACK_DAYS,
    MODEL_VERSION,
    FeatureCompatibilityError,
    get_lookback_window,
    validate_feature_payload,
)


def valid_feature_payload():
    payload = {
        feature: 0 for feature in FEATURES
    }

    payload.update(
        {
            "age": 30,
            "tenure_years": 2.5,
            "job_level": 2,
            "annual_base_salary_inr": 600000,
            "average_hours_worked_90d": 8.0,
            "average_performance_rating_90d": 3.5,
            "average_manager_feedback_score_90d": 3.5,
            "average_engagement_score_90d": 3.5,
            "average_job_satisfaction_score_90d": 3.5,
            "average_employee_nps_90d": 0.0,
            "department": "Engineering",
        }
    )

    return payload


def test_v3_schema_contains_17_features():
    assert len(FEATURES) == 17
    assert len(set(FEATURES)) == 17
    assert MODEL_VERSION == "event-based-v3"


def test_lookback_window_has_90_days():
    cutoff = date(2026, 6, 30)

    start, end = get_lookback_window(cutoff)

    assert start == cutoff - timedelta(days=90)
    assert end == cutoff
    assert (end - start).days == LOOKBACK_DAYS


def test_lookback_window_rejects_non_date_input():
    with pytest.raises(TypeError):
        get_lookback_window("2026-06-30")


def test_payload_returns_features_in_model_order():
    payload = valid_feature_payload()

    # Reverse insertion order to confirm schema order is authoritative.
    reversed_payload = dict(reversed(list(payload.items())))

    validated = validate_feature_payload(reversed_payload)

    assert list(validated.keys()) == FEATURES


def test_payload_rejects_missing_features():
    payload = valid_feature_payload()
    del payload["department"]

    with pytest.raises(FeatureCompatibilityError):
        validate_feature_payload(payload)


def test_payload_rejects_null_features():
    payload = valid_feature_payload()
    payload["average_engagement_score_90d"] = None

    with pytest.raises(FeatureCompatibilityError):
        validate_feature_payload(payload)
