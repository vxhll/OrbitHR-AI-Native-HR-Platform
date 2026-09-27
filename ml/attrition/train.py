import os
import sys

import joblib
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


PROJECT_ROOT = r"D:\OrbitHR-AI-Native-HR-Platform"

DATA_PATH = os.path.join(
    PROJECT_ROOT,
    "ml",
    "evaluation",
    "attrition_training_dataset.csv",
)

MODEL_DIR = os.path.join(
    PROJECT_ROOT,
    "ml",
    "attrition",
)

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "attrition_logistic_regression.joblib",
)


def train_model():
    print("Loading training dataset...")

    df = pd.read_csv(DATA_PATH)

    print(f"Dataset shape: {df.shape}")

    target_column = "attrited_within_180_days_label"

    feature_columns = [
        "age",
        "tenure_years",
        "annual_base_salary_inr",
        "attendance_record_count",
        "average_hours_worked",
        "absent_days",
        "average_performance_rating",
        "average_manager_feedback_score",
        "promotion_count",
        "average_engagement_score",
        "average_job_satisfaction_score",
        "average_employee_nps",
        "leave_record_count",
        "total_leave_days",
        "payroll_record_count",
    ]

    X = df[feature_columns]
    y = df[target_column]

    print(f"Features: {len(feature_columns)}")
    print(f"Samples: {len(X)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    print(f"Training samples: {len(X_train)}")
    print(f"Testing samples: {len(X_test)}")

    model = Pipeline(
        steps=[
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    random_state=42,
                ),
            ),
        ]
    )

    print("\nTraining Logistic Regression...")

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(y_test, predictions, zero_division=0)
    recall = recall_score(y_test, predictions, zero_division=0)
    f1 = f1_score(y_test, predictions, zero_division=0)
    roc_auc = roc_auc_score(y_test, probabilities)

    print("\nModel Evaluation")
    print("----------------")
    print(f"Accuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1 Score : {f1:.4f}")
    print(f"ROC-AUC  : {roc_auc:.4f}")

    print("\nClassification Report")
    print("---------------------")
    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0,
        )
    )

    print("Confusion Matrix")
    print("----------------")
    print(confusion_matrix(y_test, predictions))

    os.makedirs(MODEL_DIR, exist_ok=True)

    joblib.dump(model, MODEL_PATH)

    print("\nModel saved to:")
    print(MODEL_PATH)


if __name__ == "__main__":
    train_model()