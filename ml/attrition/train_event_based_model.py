
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
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

MODEL_PATH = (
    ROOT / "ml" / "attrition"
    / "attrition_event_based_logistic_regression.joblib"
)

METRICS_PATH = (
    ROOT / "ml" / "evaluation"
    / "event_based_attrition_metrics.json"
)

TARGET = "attrited_within_180_days_label"
GROUP = "employee_id"
DATE = "prediction_date"
AUDIT = "exit_date_for_validation_only"

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


def grouped_split(df, test_size, seed):
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=test_size,
        random_state=seed,
    )

    train_idx, test_idx = next(
        splitter.split(
            df[FEATURES],
            df[TARGET],
            groups=df[GROUP],
        )
    )

    return (
        df.iloc[train_idx].copy(),
        df.iloc[test_idx].copy(),
    )


def threshold_metrics(y_true, probabilities, threshold):
    predictions = (probabilities >= threshold).astype(int)

    return {
        "threshold": float(threshold),
        "accuracy": float(
            accuracy_score(y_true, predictions)
        ),
        "precision": float(
            precision_score(
                y_true, predictions, zero_division=0
            )
        ),
        "recall": float(
            recall_score(
                y_true, predictions, zero_division=0
            )
        ),
        "f1": float(
            f1_score(
                y_true, predictions, zero_division=0
            )
        ),
        "confusion_matrix": confusion_matrix(
            y_true,
            predictions,
            labels=[0, 1],
        ).tolist(),
    }


def require_both_classes(df, name):
    if df.empty or df[TARGET].nunique() != 2:
        raise RuntimeError(
            f"{name} must contain both target classes. "
            f"Rows={len(df)}, "
            f"labels={df[TARGET].value_counts().to_dict()}"
        )


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"V3 dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)
    df[DATE] = pd.to_datetime(df[DATE], errors="coerce")

    required = set(FEATURES + [TARGET, GROUP, DATE, AUDIT])
    missing = sorted(required - set(df.columns))

    if missing:
        raise ValueError(
            f"Dataset is missing columns: {missing}"
        )

    if df[DATE].isna().any():
        raise ValueError("Invalid prediction dates found.")

    if df[FEATURES + [TARGET, GROUP]].isna().any().any():
        raise ValueError(
            "Missing feature, target, or employee ID values."
        )

    if not set(df[TARGET].unique()).issubset({0, 1}):
        raise ValueError("Target must contain only 0 and 1.")

    if df.duplicated([GROUP, DATE]).any():
        raise ValueError("Duplicate employee/date snapshots found.")

    # Keep employees disjoint between all three splits.
    trainval_all, test_all = grouped_split(
        df, test_size=0.20, seed=42
    )
    train_all, validation_all = grouped_split(
        trainval_all, test_size=0.25, seed=43
    )

    train_groups = set(train_all[GROUP])
    validation_groups = set(validation_all[GROUP])
    test_groups = set(test_all[GROUP])

    overlap = {
        "train_validation": len(
            train_groups & validation_groups
        ),
        "train_test": len(train_groups & test_groups),
        "validation_test": len(
            validation_groups & test_groups
        ),
    }

    if any(overlap.values()):
        raise RuntimeError(
            f"Employee overlap detected: {overlap}"
        )

    # Chronological windows within each employee-disjoint split.
    train = train_all.loc[
        train_all[DATE] <= pd.Timestamp("2025-08-01")
    ].copy()

    validation = validation_all.loc[
        validation_all[DATE].between(
            pd.Timestamp("2025-09-01"),
            pd.Timestamp("2025-10-01"),
        )
    ].copy()

    test = test_all.loc[
        test_all[DATE].between(
            pd.Timestamp("2025-11-01"),
            pd.Timestamp("2025-12-01"),
        )
    ].copy()

    require_both_classes(train, "Training set")
    require_both_classes(validation, "Validation set")
    require_both_classes(test, "Test set")

    # Preprocessing is fitted only on training data.
    preprocessing = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    steps=[
                        (
                            "imputer",
                            SimpleImputer(strategy="median"),
                        ),
                        ("scaler", StandardScaler()),
                    ]
                ),
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                Pipeline(
                    steps=[
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
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ]
    )

    model = Pipeline(
        steps=[
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

    X_train = train[FEATURES]
    y_train = train[TARGET].astype(int)

    X_validation = validation[FEATURES]
    y_validation = validation[TARGET].astype(int)

    X_test = test[FEATURES]
    y_test = test[TARGET].astype(int)

    model.fit(X_train, y_train)

    # Select threshold using validation data only.
    validation_probabilities = model.predict_proba(
        X_validation
    )[:, 1]

    threshold_results = []

    for threshold in np.arange(0.10, 0.91, 0.05):
        threshold_results.append(
            threshold_metrics(
                y_validation,
                validation_probabilities,
                threshold,
            )
        )

    best_validation = max(
        threshold_results,
        key=lambda result: (
            result["f1"],
            result["precision"],
            result["threshold"],
        ),
    )

    chosen_threshold = best_validation["threshold"]

    # Evaluate on the untouched test employees.
    test_probabilities = model.predict_proba(X_test)[:, 1]
    test_predictions = (
        test_probabilities >= chosen_threshold
    ).astype(int)

    test_metrics = threshold_metrics(
        y_test, test_probabilities, chosen_threshold
    )

    test_metrics.update(
        {
            "roc_auc": float(
                roc_auc_score(y_test, test_probabilities)
            ),
            "average_precision": float(
                average_precision_score(
                    y_test, test_probabilities
                )
            ),
            "classification_report": classification_report(
                y_test,
                test_predictions,
                labels=[0, 1],
                output_dict=True,
                zero_division=0,
            ),
        }
    )

    baseline_predictions = np.zeros(len(y_test), dtype=int)

    baseline = {
        "accuracy": float(
            accuracy_score(y_test, baseline_predictions)
        ),
        "precision": float(
            precision_score(
                y_test, baseline_predictions,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                y_test, baseline_predictions,
                zero_division=0,
            )
        ),
        "f1": float(
            f1_score(
                y_test, baseline_predictions,
                zero_division=0,
            )
        ),
    }

    metrics = {
        "model": "Logistic Regression",
        "version": "event-based-v3",
        "dataset": str(DATA_PATH.relative_to(ROOT)),
        "split_strategy": (
            "Employee-disjoint GroupShuffleSplit followed by "
            "chronological filtering"
        ),
        "date_windows": {
            "train": "through 2025-08-01",
            "validation": "2025-09-01 through 2025-10-01",
            "test": "2025-11-01 through 2025-12-01",
        },
        "split_employee_counts": {
            "train": train[GROUP].nunique(),
            "validation": validation[GROUP].nunique(),
            "test": test[GROUP].nunique(),
        },
        "split_row_counts": {
            "train": len(train),
            "validation": len(validation),
            "test": len(test),
        },
        "employee_overlap": overlap,
        "label_distribution": {
            str(k): int(v)
            for k, v in df[TARGET].value_counts().items()
        },
        "positive_rate": float(df[TARGET].mean()),
        "positive_labels": {
            "train": int(y_train.sum()),
            "validation": int(y_validation.sum()),
            "test": int(y_test.sum()),
        },
        "selected_threshold": chosen_threshold,
        "validation_metrics": best_validation,
        "validation_threshold_search": threshold_results,
        "test_metrics": test_metrics,
        "majority_class_baseline": baseline,
        "features": FEATURES,
        "limitations": [
            "Synthetic data only; not real-world validation.",
            "Threshold is selected on synthetic validation data.",
            "Predictions must not independently determine "
            "employment decisions.",
        ],
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(
        {
            "pipeline": model,
            "threshold": chosen_threshold,
            "features": FEATURES,
            "version": "event-based-v3",
            "target": TARGET,
        },
        MODEL_PATH,
    )

    METRICS_PATH.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    print("\n=== ORBITHR EVENT-BASED MODEL V3 ===")
    print(f"Training rows: {len(train):,}")
    print(f"Validation rows: {len(validation):,}")
    print(f"Test rows: {len(test):,}")
    print("Employee counts:", metrics["split_employee_counts"])
    print("Employee overlap:", overlap)
    print(f"Selected threshold: {chosen_threshold:.2f}")

    print("\n=== HELD-OUT TEST METRICS ===")
    for metric in [
        "accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "average_precision",
    ]:
        print(f"{metric}: {test_metrics[metric]:.4f}")

    print(
        "Confusion matrix [[TN, FP], [FN, TP]]:",
        test_metrics["confusion_matrix"],
    )

    print("\n=== MAJORITY-CLASS BASELINE ===")
    for metric, value in baseline.items():
        print(f"{metric}: {value:.4f}")

    print(f"\nModel saved: {MODEL_PATH}")
    print(f"Metrics saved: {METRICS_PATH}")
    print("Synthetic evaluation only; not production validation.")


if __name__ == "__main__":
    main()
