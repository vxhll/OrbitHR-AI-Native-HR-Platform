import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.attrition_record import AttritionRecord
from ml.attrition.feature_service import build_attrition_features


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured")


engine = create_engine(DATABASE_URL)


def build_attrition_dataset() -> pd.DataFrame:
    with Session(engine) as db:

        employees = db.scalars(
            select(Employee)
        ).all()

        rows = []

        for employee in employees:

            employee_id = employee.employee_id

            # -------------------------
            # Shared feature engineering
            # -------------------------

            features = build_attrition_features(
                db,
                employee_id,
            )

            # -------------------------
            # Attrition target
            # -------------------------

            attrition = db.scalar(
                select(AttritionRecord).where(
                    AttritionRecord.employee_id == employee_id
                )
            )

            attrition_label = (
                attrition.attrited_within_180_days_label
                if attrition
                else None
            )

            # -------------------------
            # Final training row
            # -------------------------

            rows.append(
                {
                    "employee_id": employee_id,
                    **features,
                    "attrited_within_180_days_label": attrition_label,
                }
            )

    return pd.DataFrame(rows)


if __name__ == "__main__":

    df = build_attrition_dataset()

    print("\nOrbitHR Attrition Dataset")
    print("-------------------------")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    print("\nColumns:")

    for column in df.columns:
        print(f" - {column}")

    print("\nTarget distribution:")

    print(
        df["attrited_within_180_days_label"]
        .value_counts(dropna=False)
        .sort_index()
    )

    print("\nFirst 5 rows:")

    print(df.head())

    output_dir = os.path.join(
        os.path.dirname(__file__),
        "..",
        "evaluation",
    )

    os.makedirs(
        output_dir,
        exist_ok=True,
    )

    output_path = os.path.join(
        output_dir,
        "attrition_training_dataset.csv",
    )

    df.to_csv(
        output_path,
        index=False,
    )

    print("\nSaved dataset to:")

    print(
        os.path.abspath(output_path)
    )