
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "synthetic_v2"
    / "temporal_attrition_snapshots.csv"
)

df = pd.read_csv(DATASET_PATH, parse_dates=["prediction_date"])
df["exit_date_for_validation_only"] = pd.to_datetime(
    df["exit_date_for_validation_only"],
    errors="coerce",
)

label_col = "attrited_within_180_days_label"
audit_col = "exit_date_for_validation_only"

excluded_from_features = {
    "employee_id",
    "prediction_date",
    audit_col,
    label_col,
}

feature_cols = [
    column
    for column in df.columns
    if column not in excluded_from_features
]

print("=== TEMPORAL DATASET VALIDATION ===")
print(f"Dataset rows: {len(df)}")
print(f"Unique employees: {df['employee_id'].nunique()}")
print(f"Unique prediction dates: {df['prediction_date'].nunique()}")

checks = {}

checks["No duplicate employee/date snapshots"] = not df.duplicated(
    ["employee_id", "prediction_date"]
).any()

prediction_end = (
    df["prediction_date"] + pd.Timedelta(days=180)
)

exit_dates = df[audit_col]
labels = df[label_col]

positive_valid = (
    (labels == 1)
    & exit_dates.notna()
    & (exit_dates > df["prediction_date"])
    & (exit_dates <= prediction_end)
)

negative_valid = (
    (labels == 0)
    & (
        exit_dates.isna()
        | (exit_dates > prediction_end)
    )
)

checks["Positive labels match future exit window"] = (
    ((labels == 1) == positive_valid).all()
)

checks["Negative labels match complete outcome window"] = (
    ((labels == 0) == negative_valid).all()
)

checks["No snapshots on or after exit date"] = (
    exit_dates.isna()
    | (df["prediction_date"] < exit_dates)
).all()

checks["Labels contain only 0 and 1"] = set(
    labels.dropna().unique()
).issubset({0, 1})

checks["Both label classes are present"] = (
    labels.nunique() == 2
)

checks["No missing model features"] = (
    not df[feature_cols].isna().any().any()
)

numeric_features = df[feature_cols].select_dtypes(
    include=[np.number]
)

checks["Numeric features are finite"] = np.isfinite(
    numeric_features.to_numpy(dtype=float)
).all()

checks["Audit columns excluded from feature list"] = (
    audit_col not in feature_cols
    and label_col not in feature_cols
    and "employee_id" not in feature_cols
)

for description, passed in checks.items():
    print(f"[{'PASS' if passed else 'FAIL'}] {description}")

print("\n=== LABEL DISTRIBUTION ===")
print(df[label_col].value_counts().sort_index())

print("\n=== FEATURE COLUMNS ===")
print(feature_cols)

failed = [name for name, passed in checks.items() if not passed]

if failed:
    print("\nVALIDATION FAILED:")
    for name in failed:
        print(f"- {name}")
    raise SystemExit(1)

print("\nALL CHECKS PASSED")
