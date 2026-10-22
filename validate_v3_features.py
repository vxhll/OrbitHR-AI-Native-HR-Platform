from datetime import date

import pandas as pd

from ml.attrition.event_based_feature_service import FEATURES
from ml.attrition.event_based_prediction_service import (
    EventBasedPredictionService,
)


SNAPSHOT_PATH = "data/synthetic_v3/temporal_attrition_snapshots.csv"
SAMPLE_SIZE = 10
RANDOM_STATE = 42
TOLERANCE = 1e-9


def values_match(actual_value, expected_value):
    if isinstance(actual_value, str):
        return actual_value == str(expected_value)

    return abs(float(actual_value) - float(expected_value)) < TOLERANCE


def main():
    service = EventBasedPredictionService()

    snapshots = pd.read_csv(
        SNAPSHOT_PATH,
        usecols=["employee_id", "prediction_date"] + FEATURES,
    )
    snapshots["prediction_date"] = pd.to_datetime(
        snapshots["prediction_date"]
    ).dt.date

    if snapshots.duplicated(
        subset=["employee_id", "prediction_date"]
    ).any():
        raise SystemExit(
            "FAIL: Duplicate employee/date snapshots found."
        )

    sample = snapshots.sample(
        n=min(SAMPLE_SIZE, len(snapshots)),
        random_state=RANDOM_STATE,
    ).sort_values(["employee_id", "prediction_date"])

    total_mismatches = 0
    total_features_checked = 0

    print("Snapshots selected:", len(sample))

    for _, expected in sample.iterrows():
        employee_id = str(expected["employee_id"])
        cutoff = expected["prediction_date"]

        actual = service.build_features(
            employee_id=employee_id,
            prediction_date=cutoff,
        )

        mismatches = []

        for feature in FEATURES:
            actual_value = actual[feature]
            expected_value = expected[feature]
            total_features_checked += 1

            if not values_match(actual_value, expected_value):
                mismatches.append(
                    (feature, actual_value, expected_value)
                )

        total_mismatches += len(mismatches)

        print(
            f"{employee_id} | {cutoff} | "
            f"features={len(FEATURES)} | "
            f"mismatches={len(mismatches)}"
        )

        for feature, actual_value, expected_value in mismatches:
            print(
                f"  {feature}: service={actual_value}, "
                f"snapshot={expected_value}"
            )

    print("Snapshots checked:", len(sample))
    print("Features checked:", total_features_checked)
    print("Feature mismatches:", total_mismatches)

    if total_mismatches:
        raise SystemExit("FEATURE VALIDATION: FAIL")

    print("FEATURE VALIDATION: PASS")


if __name__ == "__main__":
    main()