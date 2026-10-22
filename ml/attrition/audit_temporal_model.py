
import json
from pathlib import Path

import joblib
import pandas as pd

from sklearn.dummy import DummyClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit


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


def split_groups(df):
    first_split = GroupShuffleSplit(
        n_splits=1,
        test_size=0.20,
        random_state=42,
    )

    trainval_idx, test_idx = next(
        first_split.split(
            df,
            df["attrited_within_180_days_label"],
            groups=df["employee_id"],
        )
    )

    trainval = df.iloc[trainval_idx]
    test = df.iloc[test_idx]

    second_split = GroupShuffleSplit(
        n_splits=1,
        test_size=0.25,
        random_state=43,
    )

    train_idx, val_idx = next(
        second_split.split(
            trainval,
            trainval["attrited_within_180_days_label"],
            groups=trainval["employee_id"],
        )
    )

    train = trainval.iloc[train_idx]
    validation = trainval.iloc[val_idx]

    return train, validation, test


def metric_summary(y_true, predictions, probabilities):
    return {
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
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "average_precision": float(
            average_precision_score(y_true, probabilities)
        ),
    }


def main():
    df = pd.read_csv(DATA_PATH)
    saved = joblib.load(MODEL_PATH)

    pipeline = saved["pipeline"]
    threshold = float(saved["threshold"])
    features = saved["features"]
    target = "attrited_within_180_days_label"

    train, validation, test = split_groups(df)

    X_test = test[features]
    y_test = test[target].astype(int)

    model_probabilities = pipeline.predict_proba(X_test)[:, 1]
    model_predictions = (
        model_probabilities >= threshold
    ).astype(int)

    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(train[features], train[target])

    baseline_predictions = baseline.predict(X_test)
    baseline_probabilities = baseline.predict_proba(X_test)[:, 1]

    print("=== HELD-OUT TEST COMPARISON ===")
    print(f"Selected model threshold: {threshold:.2f}")
    print(
        "Test positive prevalence: "
        f"{y_test.mean():.4f}"
    )

    print("\nLogistic regression:")
    for name, value in metric_summary(
        y_test,
        model_predictions,
        model_probabilities,
    ).items():
        print(f"{name}: {value:.4f}")

    print("\nMajority-class baseline:")
    for name, value in metric_summary(
        y_test,
        baseline_predictions,
        baseline_probabilities,
    ).items():
        print(f"{name}: {value:.4f}")

    # Inspect model coefficients after preprocessing.
    preprocessor = pipeline.named_steps["preprocessing"]
    classifier = pipeline.named_steps["classifier"]

    transformed_names = preprocessor.get_feature_names_out()
    coefficients = classifier.coef_[0]

    importance = pd.DataFrame(
        {
            "feature": transformed_names,
            "coefficient": coefficients,
        }
    ).sort_values("coefficient")

    print("\n=== 10 MOST NEGATIVE COEFFICIENTS ===")
    print(importance.head(10).to_string(index=False))

    print("\n=== 10 MOST POSITIVE COEFFICIENTS ===")
    print(
        importance.tail(10)
        .sort_values("coefficient", ascending=False)
        .to_string(index=False)
    )

    metrics = json.loads(
        METRICS_PATH.read_text(encoding="utf-8")
    )


    print("\n=== SPLIT CONSISTENCY ===")
    print(
        "Saved test row count matches: "
        f"{len(test) == metrics['split_row_counts']['test']}"
    )
    print(
        "Saved test employee count matches: "
        f"{test['employee_id'].nunique() == metrics['split_employee_counts']['test']}"
    )

    print(
        "\nNote: coefficients indicate direction and magnitude "
        "on the transformed feature scale; they do not prove "
        "causation."
    )


if __name__ == "__main__":
    main()
