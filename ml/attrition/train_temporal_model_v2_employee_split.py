
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
    ROOT / "data" / "synthetic_v2"
    / "temporal_attrition_snapshots.csv"
)

MODEL_PATH = (
    ROOT / "ml" / "attrition"
    / "attrition_temporal_logistic_regression.joblib"
)

METRICS_PATH = (
    ROOT / "ml" / "evaluation"
    / "temporal_attrition_metrics.json"
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

AUDIT_COLUMNS = [
    "prediction_date",
    "exit_date_for_validation_only",
]


def grouped_split(X, y, groups, test_size, seed):
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=test_size,
        random_state=seed,
    )

    train_idx, test_idx = next(
        splitter.split(X, y, groups=groups)
    )

    return train_idx, test_idx


def evaluate_at_threshold(y_true, probabilities, threshold):
    predictions = (probabilities >= threshold).astype(int)

    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(
            precision_score(y_true, predictions, zero_division=0)
        ),
        "recall": float(
            recall_score(y_true, predictions, zero_division=0)
        ),
        "f1": float(
            f1_score(y_true, predictions, zero_division=0)
        ),
        "confusion_matrix": confusion_matrix(
            y_true,
            predictions,
            labels=[0, 1],
        ).tolist(),
    }


def main():
    df = pd.read_csv(DATA_PATH)

    required = set(FEATURES + [TARGET, GROUP] + AUDIT_COLUMNS)
    missing = sorted(required - set(df.columns))

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if df[FEATURES + [TARGET, GROUP]].isna().any().any():
        raise ValueError("Missing feature, target, or group values.")

    if not set(df[TARGET].unique()).issubset({0, 1}):
        raise ValueError("Target must contain only 0 and 1.")

    # First hold out 20% of employees for final testing.
    trainval_idx, test_idx = grouped_split(
        df[FEATURES],
        df[TARGET],
        df[GROUP],
        test_size=0.20,
        seed=42,
    )

    trainval = df.iloc[trainval_idx].copy()
    test = df.iloc[test_idx].copy()

    # Split remaining 80% into 60% overall training and 20%
    # overall validation. 0.25 of 80% equals 20% overall.
    train_idx, val_idx = grouped_split(
        trainval[FEATURES],
        trainval[TARGET],
        trainval[GROUP],
        test_size=0.25,
        seed=43,
    )

    train = trainval.iloc[train_idx].copy()
    validation = trainval.iloc[val_idx].copy()

    train_groups = set(train[GROUP])
    val_groups = set(validation[GROUP])
    test_groups = set(test[GROUP])

    if (
        train_groups & val_groups
        or train_groups & test_groups
        or val_groups & test_groups
    ):
        raise RuntimeError("Employee overlap across data splits.")

    X_train = train[FEATURES]
    y_train = train[TARGET].astype(int)

    X_val = validation[FEATURES]
    y_val = validation[TARGET].astype(int)

    X_test = test[FEATURES]
    y_test = test[TARGET].astype(int)

    if y_train.nunique() < 2 or y_val.nunique() < 2:
        raise RuntimeError(
            "Training and validation sets must contain both classes."
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

    # Fit using training employees only.
    model.fit(X_train, y_train)

    # Choose threshold on validation employees only.
    val_probabilities = model.predict_proba(X_val)[:, 1]

    threshold_results = []
    for threshold in np.arange(0.10, 0.91, 0.05):
        result = evaluate_at_threshold(
            y_val,
            val_probabilities,
            threshold,
        )
        threshold_results.append(result)

    # Choose the threshold with the highest validation F1.
    # In ties, prefer higher precision, then higher threshold.
    best_validation = max(
        threshold_results,
        key=lambda item: (
            item["f1"],
            item["precision"],
            item["threshold"],
        ),
    )

    chosen_threshold = best_validation["threshold"]

    # Evaluate once on the untouched test employees.
    test_probabilities = model.predict_proba(X_test)[:, 1]
    test_predictions = (
        test_probabilities >= chosen_threshold
    ).astype(int)

    test_metrics = {
        "threshold": chosen_threshold,
        "accuracy": float(
            accuracy_score(y_test, test_predictions)
        ),
        "precision": float(
            precision_score(y_test, test_predictions, zero_division=0)
        ),
        "recall": float(
            recall_score(y_test, test_predictions, zero_division=0)
        ),
        "f1": float(
            f1_score(y_test, test_predictions, zero_division=0)
        ),
        "roc_auc": float(
            roc_auc_score(y_test, test_probabilities)
        ),
        "average_precision": float(
            average_precision_score(y_test, test_probabilities)
        ),
        "confusion_matrix": confusion_matrix(
            y_test,
            test_predictions,
            labels=[0, 1],
        ).tolist(),
        "classification_report": classification_report(
            y_test,
            test_predictions,
            labels=[0, 1],
            output_dict=True,
            zero_division=0,
        ),
    }

    metrics = {
        "model": "Logistic Regression",
        "version": "temporal-2.0",
        "dataset": str(DATA_PATH.relative_to(ROOT)),
        "split_strategy": (
            "Two-stage GroupShuffleSplit by employee_id"
        ),
        "split_employee_counts": {
            "train": len(train_groups),
            "validation": len(val_groups),
            "test": len(test_groups),
        },
        "split_row_counts": {
            "train": len(train),
            "validation": len(validation),
            "test": len(test),
        },
        "employee_overlap": {
            "train_validation": len(train_groups & val_groups),
            "train_test": len(train_groups & test_groups),
            "validation_test": len(val_groups & test_groups),
        },
        "train_positive_labels": int(y_train.sum()),
        "validation_positive_labels": int(y_val.sum()),
        "test_positive_labels": int(y_test.sum()),
        "validation_threshold_selection": (
            "Highest validation F1; ties prefer precision, then threshold"
        ),
        "selected_threshold": chosen_threshold,
        "validation_metrics_at_selected_threshold": best_validation,
        "validation_threshold_search": threshold_results,
        "test_metrics": test_metrics,
        "features": FEATURES,
        "limitations": [
            "Synthetic data only; not real-world validation.",
            "Feature aggregates are simulated, not derived from raw history.",
            "Employee-level holdout does not establish future-calendar generalization.",
            "Threshold selection optimizes synthetic validation F1 only.",
        ],
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(
        {
            "pipeline": model,
            "threshold": chosen_threshold,
            "features": FEATURES,
            "version": "temporal-2.0",
        },
        MODEL_PATH,
    )

    METRICS_PATH.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    print("=== TEMPORAL ATTRITION EVALUATION v2 ===")
    print(f"Training rows: {len(train)}")
    print(f"Validation rows: {len(validation)}")
    print(f"Test rows: {len(test)}")
    print(f"Employee counts: {metrics['split_employee_counts']}")
    print(f"Employee overlap: {metrics['employee_overlap']}")
    print(f"Selected validation threshold: {chosen_threshold:.2f}")
    print("\n=== HELD-OUT TEST METRICS ===")
    print(f"Accuracy: {test_metrics['accuracy']:.4f}")
    print(f"Precision: {test_metrics['precision']:.4f}")
    print(f"Recall: {test_metrics['recall']:.4f}")
    print(f"F1-score: {test_metrics['f1']:.4f}")
    print(f"ROC-AUC: {test_metrics['roc_auc']:.4f}")
    print(
        f"Average precision: "
        f"{test_metrics['average_precision']:.4f}"
    )
    print("Confusion matrix [[TN, FP], [FN, TP]]:")
    print(test_metrics["confusion_matrix"])
    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            test_predictions,
            labels=[0, 1],
            zero_division=0,
        )
    )
    print(f"Model saved: {MODEL_PATH}")
    print(f"Metrics saved: {METRICS_PATH}")
    print("\nSynthetic evaluation only; not production validation.")


if __name__ == "__main__":
    main()
