from pathlib import Path

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
    ROOT / "data" / "synthetic_v3"
    / "temporal_attrition_snapshots.csv"
)

OUTPUT_PATH = (
    ROOT / "ml" / "evaluation"
    / "event_based_chronological_metrics.txt"
)

TARGET = "attrited_within_180_days_label"
GROUP = "employee_id"
DATE = "prediction_date"

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
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"V3 dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)
    df[DATE] = pd.to_datetime(df[DATE])

    required_columns = (
        FEATURES + [TARGET, GROUP, DATE]
    )

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    if df[required_columns].isnull().any().any():
        raise ValueError(
            "Missing values found in required columns. "
            "Investigate before evaluation."
        )

    if not set(df[TARGET].unique()).issubset({0, 1}):
        raise ValueError(
            "Target must contain binary labels 0 and 1."
        )

    # Hold out entire employee groups first.
    outer_splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.20,
        random_state=2026,
    )

    development_idx, test_idx = next(
        outer_splitter.split(
            df,
            df[TARGET],
            groups=df[GROUP],
        )
    )

    development = df.iloc[development_idx].copy()
    test_employees = df.iloc[test_idx].copy()

    # Training/validation groups are also disjoint.
    development_employee_ids = (
        development[GROUP].drop_duplicates()
    )

    validation_splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.25,
        random_state=2027,
    )

    train_group_idx, validation_group_idx = next(
        validation_splitter.split(
            development_employee_ids.to_frame(),
            groups=development_employee_ids,
        )
    )

    train_employee_ids = set(
        development_employee_ids.iloc[train_group_idx]
    )

    validation_employee_ids = set(
        development_employee_ids.iloc[
            validation_group_idx
        ]
    )

    # Apply chronological windows after employee assignment.
    train = development[
        development[GROUP].isin(train_employee_ids)
        & development[DATE].between(
            "2025-01-01", "2025-08-01"
        )
    ].copy()

    validation = development[
        development[GROUP].isin(validation_employee_ids)
        & development[DATE].between(
            "2025-09-01", "2025-10-01"
        )
    ].copy()

    test = test_employees[
        test_employees[DATE].between(
            "2025-11-01", "2025-12-01"
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
        raise RuntimeError(
            "Employee overlap detected between splits."
        )

    splits = {
        "training": train,
        "validation": validation,
        "test": test,
    }

    for name, part in splits.items():
        if part.empty:
            raise RuntimeError(
                f"{name} split is empty."
            )

        if part[TARGET].nunique() < 2:
            raise RuntimeError(
                f"{name} split does not contain "
                "both target classes."
            )

    # Fit preprocessing only on training data.
    preprocessing = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline([
                    (
                        "imputer",
                        SimpleImputer(strategy="median"),
                    ),
                    ("scaler", StandardScaler()),
                ]),
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                Pipeline([
                    (
                        "imputer",
                        SimpleImputer(
                            strategy="most_frequent"
                        ),
                    ),
                    (
                        "onehot",
                        OneHotEncoder(
                            handle_unknown="ignore"
                        ),
                    ),
                ]),
                CATEGORICAL_FEATURES,
            ),
        ]
    )

    model = Pipeline([
        ("preprocessing", preprocessing),
        (
            "classifier",
            LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                random_state=42,
            ),
        ),
    ])

    model.fit(
        train[FEATURES],
        train[TARGET].astype(int),
    )

    # Select the operating threshold on validation only.
    validation_probabilities = model.predict_proba(
        validation[FEATURES]
    )[:, 1]

    threshold_results = []

    for threshold in [
        0.20, 0.25, 0.30, 0.35, 0.40,
        0.45, 0.50, 0.55, 0.60, 0.65, 0.70,
    ]:
        validation_predictions = (
            validation_probabilities >= threshold
        ).astype(int)

        threshold_results.append({
            "threshold": threshold,
            "precision": precision_score(
                validation[TARGET],
                validation_predictions,
                zero_division=0,
            ),
            "recall": recall_score(
                validation[TARGET],
                validation_predictions,
                zero_division=0,
            ),
            "f1": f1_score(
                validation[TARGET],
                validation_predictions,
                zero_division=0,
            ),
        })

    best = max(
        threshold_results,
        key=lambda result: (
            result["f1"],
            result["precision"],
            result["threshold"],
        ),
    )

    threshold = best["threshold"]

    # Evaluate once on the held-out test set.
    test_probabilities = model.predict_proba(
        test[FEATURES]
    )[:, 1]

    test_predictions = (
        test_probabilities >= threshold
    ).astype(int)

    y_test = test[TARGET].astype(int)

    metrics = {
        "accuracy": accuracy_score(
            y_test, test_predictions
        ),
        "precision": precision_score(
            y_test, test_predictions,
            zero_division=0,
        ),
        "recall": recall_score(
            y_test, test_predictions,
            zero_division=0,
        ),
        "f1": f1_score(
            y_test, test_predictions,
            zero_division=0,
        ),
        "roc_auc": roc_auc_score(
            y_test, test_probabilities
        ),
        "average_precision": average_precision_score(
            y_test, test_probabilities
        ),
    }

    # Majority-class baseline.
    baseline = DummyClassifier(
        strategy="most_frequent"
    )

    baseline.fit(
        train[FEATURES],
        train[TARGET].astype(int),
    )

    baseline_predictions = baseline.predict(
        test[FEATURES]
    )

    baseline_probabilities = baseline.predict_proba(
        test[FEATURES]
    )[:, 1]

    baseline_metrics = {
        "accuracy": accuracy_score(
            y_test, baseline_predictions
        ),
        "precision": precision_score(
            y_test, baseline_predictions,
            zero_division=0,
        ),
        "recall": recall_score(
            y_test, baseline_predictions,
            zero_division=0,
        ),
        "f1": f1_score(
            y_test, baseline_predictions,
            zero_division=0,
        ),
        "roc_auc": roc_auc_score(
            y_test, baseline_probabilities
        ),
        "average_precision": average_precision_score(
            y_test, baseline_probabilities
        ),
    }

    lines = [
        "ORBIT HR - V3 EVENT-BASED HOLDOUT EVALUATION",
        "Synthetic data only; not production validation.",
        "",
        f"Total snapshots: {len(df)}",
        f"Total employees: {df[GROUP].nunique()}",
        f"Training rows: {len(train)}",
        f"Validation rows: {len(validation)}",
        f"Test rows: {len(test)}",
        f"Training employees: {len(train_ids)}",
        f"Validation employees: {len(validation_ids)}",
        f"Test employees: {len(test_ids)}",
        (
            "Employee overlaps: "
            f"train-validation={len(train_ids & validation_ids)}, "
            f"train-test={len(train_ids & test_ids)}, "
            f"validation-test={len(validation_ids & test_ids)}"
        ),
        "",
        (
            "Training date range: "
            f"{train[DATE].min().date()} to "
            f"{train[DATE].max().date()}"
        ),
        (
            "Validation date range: "
            f"{validation[DATE].min().date()} to "
            f"{validation[DATE].max().date()}"
        ),
        (
            "Test date range: "
            f"{test[DATE].min().date()} to "
            f"{test[DATE].max().date()}"
        ),
        "",
        f"Selected validation threshold: {threshold:.2f}",
        f"Validation F1: {best['f1']:.4f}",
        f"Validation precision: {best['precision']:.4f}",
        f"Validation recall: {best['recall']:.4f}",
        "",
        f"Test positive count: {int(y_test.sum())}",
        (
            "Test positive rate: "
            f"{y_test.mean():.4f}"
        ),
        "",
        "HELD-OUT TEST - LOGISTIC REGRESSION",
    ]

    lines.extend(
        f"{key}: {value:.4f}"
        for key, value in metrics.items()
    )

    lines.extend([
        "Confusion matrix [[TN, FP], [FN, TP]]:",
        str(
            confusion_matrix(
                y_test, test_predictions
            ).tolist()
        ),
        "",
        "HELD-OUT TEST - MAJORITY-CLASS BASELINE",
    ])

    lines.extend(
        f"{key}: {value:.4f}"
        for key, value in baseline_metrics.items()
    )

    lines.extend([
        "",
        "Classification report:",
        classification_report(
            y_test,
            test_predictions,
            zero_division=0,
        ),
        (
            "Limitations: all records are synthetic; "
            "results do not establish real-world performance."
        ),
        (
            "Employee groups are disjoint, and each split "
            "uses its assigned calendar window."
        ),
        (
            "This is not a pure future-time test on the same "
            "employee population. Snapshot labels have "
            "overlapping 180-day outcome windows."
        ),
        (
            "Threshold selection optimizes validation F1; "
            "it is not a calibrated employment decision rule."
        ),
    ])

    report = "\n".join(lines)

    OUTPUT_PATH.parent.mkdir(
        parents=True, exist_ok=True
    )

    OUTPUT_PATH.write_text(
        report,
        encoding="utf-8",
    )

    print(report)
    print(f"\nReport saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()