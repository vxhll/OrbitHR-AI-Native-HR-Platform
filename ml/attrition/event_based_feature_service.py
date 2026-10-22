from __future__ import annotations

from datetime import date, timedelta
from typing import Any


MODEL_VERSION = "event-based-v3"
LOOKBACK_DAYS = 90

NUMERIC_FEATURES = [
    "age",
    "tenure_years",
    "job_level",
    "annual_base_salary_inr",
    "attendance_record_count_90d",
    "average_hours_worked_90d",
    "absent_days_90d",
    "average_performance_rating_90d",
    "average_manager_feedback_score_90d",
    "promotion_count_90d",
    "average_engagement_score_90d",
    "average_job_satisfaction_score_90d",
    "average_employee_nps_90d",
    "leave_record_count_90d",
    "total_leave_days_90d",
    "payroll_record_count_90d",
]

CATEGORICAL_FEATURES = ["department"]

FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


class FeatureCompatibilityError(ValueError):
    """Raised when source data cannot safely reproduce v3 features."""


def get_lookback_window(
    prediction_date: date,
) -> tuple[date, date]:
    """
    Return the v3 lookback boundaries.

    The window is [prediction_date - 90 days, prediction_date).
    The start is inclusive; the prediction date is exclusive.
    """
    if not isinstance(prediction_date, date):
        raise TypeError("prediction_date must be a datetime.date.")

    window_start = prediction_date - timedelta(days=LOOKBACK_DAYS)

    return window_start, prediction_date


def validate_feature_payload(
    feature_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Validate a feature payload against the v3 model schema.

    This function validates schema completeness only. It does not establish
    that operational database values are temporally compatible with training.
    """
    missing = [
        feature for feature in FEATURES
        if feature not in feature_data
    ]

    if missing:
        raise FeatureCompatibilityError(
            f"Missing v3 model features: {missing}"
        )

    validated = {feature: feature_data[feature] for feature in FEATURES}

    null_features = [
        feature for feature, value in validated.items()
        if value is None
    ]

    if null_features:
        raise FeatureCompatibilityError(
            f"Null v3 model features: {null_features}"
        )

    return validated
