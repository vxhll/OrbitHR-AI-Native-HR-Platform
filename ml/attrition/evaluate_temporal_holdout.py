
from pathlib import Path

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = (
    ROOT / "data" / "synthetic_v2"
    / "temporal_attrition_snapshots.csv"
)

OUTPUT_PATH = (
    ROOT / "ml" / "evaluation"
    / "temporal_chronological_metrics.txt"
)

TARGET = "attrited_within_180_days_label"
GROUP = "employee_id"

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


def main():
    df = pd.read_csv(DATA_PATH)
    df["prediction_date"] = pd.to_datetime(df["prediction_date"])

    # Assign employee groups independently of outcomes.
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.20,
        random_state=2026,
    )

    development_idx, test_employee_idx = next(
        splitter.split(
            df,
            groups=df[GROUP],
        )
    )

    development = df.iloc[development_idx].copy()
    test_employees = df.iloc[test_employee_idx].copy()

    # Use the selected employee group only in November and December.
    test = test_employees[
        test_employees["prediction_date"].between(
            "2025-11-01", "2025-12-31"
        )
    ].copy()

    # Remaining employees are assigned to training or validation.
    development_employees = development[GROUP].drop_duplicates()

    validation_splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.25,
        random_state=2027,
    )

    train_group_idx, validation_group_idx = next(
        validation_splitter.split(
            development_employees.to_frame(),
            groups=development_employees,
        )
    )

    train_employee_ids = set(
        development_employees.iloc[train_group_idx]
    )
    validation_employee_ids = set(
        development_employees.iloc[validation_group_idx]
    )

    train = development[
        development[GROUP].isin(train_employee_ids)
        & development["prediction_date"].between(
            "2025-01-01", "2025-08-31"
        )
    ].copy()

    validation = development[
        development[GROUP].isin(validation_employee_ids)
        & development["prediction_date"].between(
            "2025-09-01", "2025-10-31"
        )
    ].copy()

    train_ids = set(train[GROUP])
    validation_ids = set(validation[GROUP])
    test_ids = set(test[GROUP])

    if (
        train_ids & validation_ids
        or train_ids & test_ids
        or validation_ids & test_ids
    ):
        raise RuntimeError("Employee overlap found between splits.")

    if train.empty or validation.empty or test.empty:
        raise RuntimeError("One or more chronological splits are empty.")

    for name, part in [
        ("training", train),
        ("validation", validation),
        ("test", test),
    ]:
        if part[TARGET].nunique() < 2:
            raise RuntimeError(
                f"{name} split does not contain both label classes."
            )

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(strategy="most_frequent"),
                        ),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore"),
                        ),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ]
    )

    model = Pipeline(
        [
            ("preprocessing", preprocessing),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )

    model.fit(train[FEATURES], train[TARGET].astype(int))

    validation_probabilities = model.predict_proba(
        validation[FEATURES]
    )[:, 1]

    # Choose the threshold using validation data only.
    threshold_results = []

    for threshold in [
        0.20, 0.25, 0.30, 0.35, 0.40,
        0.45, 0.50, 0.55, 0.60, 0.65, 0.70,
    ]:
        predictions = (
            validation_probabilities >= threshold
        ).astype(int)

        threshold_results.append(
            {
                "threshold": threshold,
                "precision": precision_score(
                    validation[TARGET],
                    predictions,
                    zero_division=0,
                ),
                "recall": recall_score(
                    validation[TARGET],
                    predictions,
                    zero_division=0,
                ),
                "f1": f1_score(
                    validation[TARGET],
                    predictions,
                    zero_division=0,
                ),
            }
        )

    best = max(
        threshold_results,
        key=lambda item: (
            item["f1"],
            item["precision"],
            item["threshold"],
        ),
    )

    threshold = best["threshold"]

    test_probabilities = model.predict_proba(
        test[FEATURES]
    )[:, 1]

    test_predictions = (
        test_probabilities >= threshold
    ).astype(int)

    y_test = test[TARGET].astype(int)

    metrics = {
        "accuracy": accuracy_score(y_test, test_predictions),
        "precision": precision_score(
            y_test, test_predictions, zero_division=0
        ),
        "recall": recall_score(
            y_test, test_predictions, zero_division=0
        ),
        "f1": f1_score(
            y_test, test_predictions, zero_division=0
        ),
        "roc_auc": roc_auc_score(y_test, test_probabilities),
        "average_precision": average_precision_score(
            y_test, test_probabilities
        ),
    }

    # Majority-class baseline fitted on training data only.
    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(train[FEATURES], train[TARGET])

    baseline_predictions = baseline.predict(test[FEATURES])
    baseline_probabilities = baseline.predict_proba(
        test[FEATURES]
    )[:, 1]

    baseline_metrics = {
        "accuracy": accuracy_score(y_test, baseline_predictions),
        "precision": precision_score(
            y_test, baseline_predictions, zero_division=0
        ),
        "recall": recall_score(
            y_test, baseline_predictions, zero_division=0
        ),
        "f1": f1_score(
            y_test, baseline_predictions, zero_division=0
        ),
        "roc_auc": roc_auc_score(y_test, baseline_probabilities),
        "average_precision": average_precision_score(
            y_test, baseline_probabilities
        ),
    }

    lines = [
        "ORBIT HR — CHRONOLOGICAL HOLDOUT EVALUATION",
        "Synthetic data only; not production validation.",
        "",
        f"Training rows: {len(train)}",
        f"Validation rows: {len(validation)}",
        f"Test rows: {len(test)}",
        f"Training employees: {len(train_ids)}",
        f"Validation employees: {len(validation_ids)}",
        f"Test employees: {len(test_ids)}",
        f"Employee overlaps: train-validation={len(train_ids & validation_ids)}, "
        f"train-test={len(train_ids & test_ids)}, "
        f"validation-test={len(validation_ids & test_ids)}",
        "",
        f"Selected validation threshold: {threshold:.2f}",
        f"Validation F1 at threshold: {best['f1']:.4f}",
        "",
        "HELD-OUT TEST — LOGISTIC REGRESSION",
    ]

    lines.extend(
        f"{key}: {value:.4f}"
        for key, value in metrics.items()
    )

    lines.extend(
        [
            "Confusion matrix [[TN, FP], [FN, TP]]:",
            str(confusion_matrix(y_test, test_predictions).tolist()),
            "",
            "HELD-OUT TEST — MAJORITY-CLASS BASELINE",
        ]
    )

    lines.extend(
        f"{key}: {value:.4f}"
        for key, value in baseline_metrics.items()
    )

    lines.extend(
        [
            "",
            "Classification report:",
            classification_report(
                y_test,
                test_predictions,
                zero_division=0,
            ),
            "Limitations: features are simulated aggregates, not raw historical records.",
            "This evaluation tests later dates and unseen employee groups,",
            "but does not prove real-world attrition forecasting performance.",
        ]
    )

    report = "\n".join(lines)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nReport saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
