
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 42
EMPLOYEE_COUNT = 1200
OUTCOME_HORIZON_DAYS = 180

PREDICTION_DATES = pd.date_range(
    start="2025-01-01",
    end="2025-12-01",
    freq="MS",
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "synthetic_v2"

rng = np.random.default_rng(SEED)


def sigmoid(value):
    return 1.0 / (1.0 + np.exp(-value))


def generate_employees():
    """Create synthetic employee attributes and exit events."""
    employees = []

    start_date = pd.Timestamp("2015-01-01")
    end_date = pd.Timestamp("2025-11-15")
    total_days = (end_date - start_date).days

    simulation_end = (
        PREDICTION_DATES.max()
        + pd.Timedelta(days=OUTCOME_HORIZON_DAYS)
    )

    for i in range(EMPLOYEE_COUNT):
        employee_id = f"SYN{i + 1:05d}"

        hire_date = start_date + pd.Timedelta(
            days=int(rng.integers(0, total_days + 1))
        )

        age = int(rng.integers(22, 57))
        job_level = int(rng.integers(1, 6))

        salary_by_level = {
            1: (300000, 600000),
            2: (450000, 900000),
            3: (700000, 1400000),
            4: (1100000, 2200000),
            5: (1800000, 3500000),
        }

        salary_low, salary_high = salary_by_level[job_level]
        salary = int(rng.integers(salary_low, salary_high))

        department = str(
            rng.choice(
                [
                    "Engineering",
                    "Sales",
                    "Human Resources",
                    "Finance",
                    "Operations",
                    "Customer Support",
                ]
            )
        )

        # Used only to simulate outcomes; never exported as a feature.
        latent_risk = float(rng.normal(0, 1))

        baseline_engagement = float(
            np.clip(
                rng.normal(3.7 - 0.25 * latent_risk, 0.55),
                1.0,
                5.0,
            )
        )

        baseline_satisfaction = float(
            np.clip(
                rng.normal(3.6 - 0.22 * latent_risk, 0.60),
                1.0,
                5.0,
            )
        )

        # Simulate at most one exit event, never before hire.
        exit_date = None
        active = True

        simulation_start = max(
            hire_date,
            pd.Timestamp("2025-01-01"),
        )

        month_start = simulation_start

        while active and month_start <= simulation_end:
            monthly_hazard = float(
                sigmoid(-4.0 + 0.85 * latent_risk)
            )

            if rng.random() < monthly_hazard:
                next_month = (
                    month_start + pd.offsets.MonthBegin(1)
                )

                last_day = min(
                    next_month - pd.Timedelta(days=1),
                    simulation_end,
                )

                available_days = (
                    last_day - month_start
                ).days + 1

                exit_date = month_start + pd.Timedelta(
                    days=int(rng.integers(0, available_days))
                )

                active = False

            month_start += pd.offsets.MonthBegin(1)

        employees.append(
            {
                "employee_id": employee_id,
                "hire_date": hire_date,
                "age": age,
                "department": department,
                "job_level": job_level,
                "annual_base_salary_inr": salary,
                "latent_risk": latent_risk,
                "baseline_engagement": baseline_engagement,
                "baseline_satisfaction": baseline_satisfaction,
                "exit_date": exit_date,
            }
        )

    return employees


def build_snapshot(employee, prediction_date):
    """Build a synthetic snapshot for one employee and date."""
    hire_date = employee["hire_date"]
    exit_date = employee["exit_date"]

    if hire_date >= prediction_date:
        return None

    # Exclude employees who have already exited.
    if exit_date is not None and exit_date <= prediction_date:
        return None

    tenure_years = max(
        0.0,
        (prediction_date - hire_date).days / 365.25,
    )

    latent_risk = employee["latent_risk"]

    # Feature generation does not use the realized future exit date.
    pre_exit_factor = 0.0

    attendance_days = int(rng.integers(60, 66))

    absent_days = int(
        np.clip(
            rng.poisson(
                2.0 + 0.8 * max(latent_risk, 0)
                + 2.0 * pre_exit_factor
            ),
            0,
            20,
        )
    )

    average_hours = float(
        np.clip(
            rng.normal(
                8.2 + 0.25 * latent_risk
                + 0.7 * pre_exit_factor,
                0.55,
            ),
            5.0,
            12.0,
        )
    )

    performance_rating = float(
        np.clip(
            rng.normal(
                3.6 - 0.18 * latent_risk
                - 0.45 * pre_exit_factor,
                0.45,
            ),
            1.0,
            5.0,
        )
    )

    manager_feedback = float(
        np.clip(
            rng.normal(
                3.6 - 0.20 * latent_risk
                - 0.55 * pre_exit_factor,
                0.50,
            ),
            1.0,
            5.0,
        )
    )

    engagement = float(
        np.clip(
            rng.normal(
                employee["baseline_engagement"]
                - 0.9 * pre_exit_factor,
                0.35,
            ),
            1.0,
            5.0,
        )
    )

    satisfaction = float(
        np.clip(
            rng.normal(
                employee["baseline_satisfaction"]
                - 0.75 * pre_exit_factor,
                0.40,
            ),
            1.0,
            5.0,
        )
    )

    employee_nps = int(
        np.clip(
            round(
                rng.normal(
                    6.5 - 0.8 * latent_risk
                    - 1.2 * pre_exit_factor,
                    1.8,
                )
            ),
            0,
            10,
        )
    )

    leave_count = int(
        np.clip(
            rng.poisson(0.7 + 0.7 * pre_exit_factor),
            0,
            6,
        )
    )

    total_leave_days = int(
        np.clip(
            rng.poisson(3.0 + 2.0 * pre_exit_factor),
            0,
            30,
        )
    )

    promotion_count = int(
        rng.random() < min(0.10, 0.015 * tenure_years)
    )

    # The label uses the future outcome window, not future features.
    outcome_end = (
        prediction_date
        + pd.Timedelta(days=OUTCOME_HORIZON_DAYS)
    )

    label = int(
        exit_date is not None
        and prediction_date < exit_date <= outcome_end
    )

    return {
        "employee_id": employee["employee_id"],
        "prediction_date": prediction_date.date().isoformat(),
        "age": employee["age"],
        "tenure_years": round(tenure_years, 3),
        "department": employee["department"],
        "job_level": employee["job_level"],
        "annual_base_salary_inr": employee[
            "annual_base_salary_inr"
        ],
        "attendance_record_count_90d": attendance_days,
        "average_hours_worked_90d": round(average_hours, 3),
        "absent_days_90d": absent_days,
        "average_performance_rating_90d": round(
            performance_rating, 3
        ),
        "average_manager_feedback_score_90d": round(
            manager_feedback, 3
        ),
        "promotion_count_90d": promotion_count,
        "average_engagement_score_90d": round(engagement, 3),
        "average_job_satisfaction_score_90d": round(
            satisfaction, 3
        ),
        "average_employee_nps_90d": employee_nps,
        "leave_record_count_90d": leave_count,
        "total_leave_days_90d": total_leave_days,
        "payroll_record_count_90d": 3,
        # Audit-only field. Never use as a model feature.
        "exit_date_for_validation_only": (
            exit_date.date().isoformat()
            if exit_date is not None
            else None
        ),
        "attrited_within_180_days_label": label,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    employees = generate_employees()
    rows = []

    for employee in employees:
        for prediction_date in PREDICTION_DATES:
            snapshot = build_snapshot(employee, prediction_date)

            if snapshot is not None:
                rows.append(snapshot)

    dataset = pd.DataFrame(rows)

    if dataset.empty:
        raise RuntimeError("No temporal snapshots were generated.")

    output_file = OUTPUT_DIR / "temporal_attrition_snapshots.csv"
    dataset.to_csv(output_file, index=False)

    positive_count = int(
        dataset["attrited_within_180_days_label"].sum()
    )
    negative_count = len(dataset) - positive_count

    readme = f"""# OrbitHR Temporal Synthetic Dataset

Generated by: ml/attrition/generate_temporal_dataset.py

- Synthetic employees: {EMPLOYEE_COUNT}
- Random seed: {SEED}
- Prediction dates: {PREDICTION_DATES.min().date()} through
  {PREDICTION_DATES.max().date()}
- Feature lookback design: preceding 90 days
- Outcome horizon: {OUTCOME_HORIZON_DAYS} calendar days
- Snapshot rows: {len(dataset)}
- Positive labels: {positive_count}
- Negative labels: {negative_count}

## Label
The label is 1 when an exit occurs after the prediction date and
on or before prediction_date + 180 days. Otherwise it is 0.

## Important limitations
This is synthetic data for pipeline development, not evidence of
real-world attrition prediction accuracy. Feature values are
simulated rather than calculated from raw daily records.

The exit_date_for_validation_only column is for label auditing
only and must never be passed to the model as a feature.
The latent risk used during generation is not exported.

The 90-day feature window is a design assumption. This generator
simulates window-level aggregates instead of raw daily history.
"""

    (OUTPUT_DIR / "README.md").write_text(
        readme,
        encoding="utf-8",
    )

    print(f"Dataset saved: {output_file}")
    print(f"Rows: {len(dataset)}")
    print(f"Unique employees: {dataset['employee_id'].nunique()}")
    print(f"Positive labels: {positive_count}")
    print(f"Negative labels: {negative_count}")
    print("\nLabels by prediction date:")
    print(
        dataset.groupby("prediction_date")[
            "attrited_within_180_days_label"
        ].agg(["count", "sum"])
    )

    # Data integrity checks before accepting the generated dataset.
    hired_before_exit = dataset.apply(
        lambda row: (
            pd.isna(row["exit_date_for_validation_only"])
            or pd.to_datetime(
                row["exit_date_for_validation_only"]
            ) >= pd.to_datetime(
                employees[
                    int(row["employee_id"][3:]) - 1
                ]["hire_date"]
            )
        ),
        axis=1,
    ).all()

    if not hired_before_exit:
        raise RuntimeError("An exit date occurs before hire date.")

    print("Hire-date/exit-date integrity check: PASS")


if __name__ == "__main__":
    main()
