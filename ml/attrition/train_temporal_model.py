
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


# ============================================================
# CONFIGURATION
# ============================================================

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


# Chronological evaluation periods.
TRAIN_END = pd.Timestamp("2025-08-01")
VALIDATION_START = pd.Timestamp("2025-09-01")
VALIDATION_END = pd.Timestamp("2025-10-01")
TEST_START = pd.Timestamp("2025-11-01")
TEST_END = pd.Timestamp("2025-12-01")


# ============================================================
# EMPLOYEE-GROUPED SPLITTING
# ============================================================

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


# ============================================================
# METRICS
# ============================================================

def threshold_metrics(y_true, probabilities, threshold):
    predictions = (
        probabilities >= threshold
    ).astype(int)

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
    if df.empty:
        raise RuntimeError(
            f"{name} is empty after applying date filters."
        )

    if df[TARGET].nunique() != 2:
        raise RuntimeError(
            f"{name} must contain both target classes. "
            f"Distribution: {df[TARGET].value_counts().to_dict()}"
        )


# ============================================================
# MAIN TRAINING PIPELINE
# ============================================================

def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"V3 dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)
    df[DATE] = pd.to_datetime(
        df[DATE], errors="coerce"
    )

    required_columns = set(
        FEATURES + [TARGET, GROUP, DATE, AUDIT]
    )

    missing_columns = sorted(
        required_columns - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Dataset is missing columns: {missing_columns}"
        )

    if df[DATE].isna().any():
        raise ValueError(
            "Dataset contains invalid prediction dates."
        )

    if df[FEATURES + [TARGET, GROUP]].isna().any().any():
        raise ValueError(
            "Model features, target, or employee IDs contain "
            "missing values. Validate the dataset first."
        )

    if not set(df[TARGET].unique()).issubset({0, 1}):
        raise ValueError(
            "Target must contain only 0 and 1."
        )

    if df.duplicated([GROUP, DATE]).any():
        raise ValueError(
            "Duplicate employee/date snapshots detected."
        )

    if df[GROUP].nunique() < 10:
        raise ValueError(
            "Not enough distinct employees for grouped evaluation."
        )

    # --------------------------------------------------------
    # Split employees first, before applying date windows.
    #
    # Approximately 60% train employees,
    # 20% validation employees,
    # 20% test employees.
    # --------------------------------------------------------

    trainval_all, test_all = grouped_split(
        df,
        test_size=0.20,
        seed=42,
    )

    train_all, validation_all = grouped_split(
        trainval_all,
        test_size=0.25,
        seed=43,
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

    # --------------------------------------------------------
    # Apply chronological windows to the disjoint employees.
    # --------------------------------------------------------

    train = train_all.loc[
        train_all[DATE] <= TRAIN_END
    ].copy()

    validation = validation_all.loc[
        validation_all[DATE].between(
            VALIDATION_START,
            VALIDATION_END,
        )
    ].copy()

    test = test_all.loc[
        test_all[DATE].between(
            TEST_START,
            TEST_END,
        )
    ].copy()

    require_both_classes(train, "Training set")
    require_both_classes(validation, "Validation set")
    require_both_classes(test, "Test set")

    # Verify employee separation after filtering as well.
    actual_train_groups = set(train[GROUP])
    actual_validation_groups = set(validation[GROUP])
    actual_test_groups = set(test[GROUP])

    if (
        actual_train_groups & actual_validation_groups
        or actual_train_groups & actual_test_groups
        or actual_validation_groups & actual_test_groups
    ):
        raise RuntimeError(
            "Employee overlap found after date filtering."
        )

    X_train = train[FEATURES]
    y_train = train[TARGET].astype(int)

    X_validation = validation[FEATURES]
    y_validation = validation[TARGET].astype(int)

    X_test = test[FEATURES]
    y_test = test[TARGET].astype(int)

    # --------------------------------------------------------
    # Preprocessing
    # --------------------------------------------------------

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

    # Fit only on training employees and training-period rows.
    model.fit(X_train, y_train)

    # --------------------------------------------------------
    # Choose threshold using validation employees only.
    # --------------------------------------------------------

    validation_probabilities = model.predict_proba(
        X_validation
    )[:, 1]

    threshold_results = []

    for threshold in np.arange(0.10, 0.91, 0.05):
        result = threshold_metrics(
            y_validation,
            validation_probabilities,
            threshold,
        )
        threshold_results.append(result)

    best_validation = max(
        threshold_results,
        key=lambda item: (
            item["f1"],
            item["precision"],
            item["threshold"],
        ),
    )

    chosen_threshold = best_validation["threshold"]

    # --------------------------------------------------------
    # Final evaluation on untouched test employees and dates.
    # --------------------------------------------------------

    test_probabilities = model.predict_proba(
        X_test
    )[:, 1]

    test_predictions = (
        test_probabilities >= chosen_threshold
    ).astype(int)

    test_metrics = threshold_metrics(
        y_test,
        test_probabilities,
        chosen_threshold,
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

    # Majority-class baseline: always predict no attrition.
    baseline_predictions = np.zeros(
        len(y_test), dtype=int
    )

    majority_baseline = {
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
        "positive_prediction_count": 0,
    }

    # --------------------------------------------------------
    # Save versioned model and metrics.
    # --------------------------------------------------------

    metrics = {
        "model": "Logistic Regression",
        "version": "event-based-v3",
        "dataset": str(DATA_PATH.relative_to(ROOT)),
        "split_strategy": (
            "Employee-disjoint groups with chronological "
            "train, validation, and test windows"
        ),
        "date_windows": {
            "train": f"through {TRAIN_END.date()}",
            "validation": (
                f"{VALIDATION_START.date()} to "
                f"{VALIDATION_END.date()}"
            ),
            "test": (
                f"{TEST_START.date()} to {TEST_END.date()}"
            ),
        },
        "split_employee_counts": {
            "train": len(actual_train_groups),
            "validation": len(actual_validation_groups),
            "test": len(actual_test_groups),
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
        "train_positive_labels": int(y_train.sum()),
        "validation_positive_labels": int(
            y_validation.sum()
        ),
        "test_positive_labels": int(y_test.sum()),
        "threshold_selection": (
            "Highest validation F1; ties prefer precision, "
            "then higher threshold"
        ),
        "selected_threshold": chosen_threshold,
        "validation_metrics_at_selected_threshold": (
            best_validation
        ),
        "validation_threshold_search": threshold_results,
        "test_metrics": test_metrics,
        "majority_class_baseline": majority_baseline,
        "features": FEATURES,
        "limitations": [
            "Synthetic data only; not real-world validation.",
            "Performance does not establish real-world "
            "attrition prediction accuracy.",
            "Threshold selection optimizes synthetic "
            "validation F1 only.",
            "Model predictions must not independently "
            "determine employment decisions.",
        ],
    }

    MODEL_PATH.parent.mkdir(
        parents=True, exist_ok=True
    )
    METRICS_PATH.parent.mkdir(
        parents=True, exist_ok=True
    )

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

    # --------------------------------------------------------
    # Console report
    # --------------------------------------------------------

    print("\n=== ORBITHR EVENT-BASED MODEL V3 ===")
    print(f"Dataset: {DATA_PATH}")
    print(f"Training rows: {len(train):,}")
    print(f"Validation rows: {len(validation):,}")
    print(f"Test rows: {len(test):,}")

    print("\nEmployee counts:")
    print(metrics["split_employee_counts"])

    print("\nEmployee overlap:")
    print(overlap)

    print("\nDate windows:")
    print(metrics["date_windows"])

    print(
        f"\nSelected validation threshold: "
        f"{chosen_threshold:.2f}"
    )

    print("\n=== HELD-OUT TEST METRICS ===")
    for metric in [
        "accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "average_precision",
    ]:
        print(
            f"{metric}: {test_metrics[metric]:.4f}"
        )

    print(
        "Confusion matrix [[TN, FP], [FN, TP]]:"
    )
    print(test_metrics["confusion_matrix"])

    print("\n=== MAJORITY-CLASS BASELINE ===")
    for metric, value in majority_baseline.items():
        print(f"{metric}: {value}")

    print(f"\nModel saved: {MODEL_PATH}")
    print(f"Metrics saved: {METRICS_PATH}")
    print(
        "\nSynthetic-data experiment only; "
        "not production validation."
    )


if __name__ == "__main__":
    main()
