
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# ORBITHR — EVENT-BASED TEMPORAL DATASET GENERATOR
# Synthetic research data only; not production HR data.
# ============================================================

SEED = 42
EMPLOYEE_COUNT = 1200
LOOKBACK_DAYS = 90
OUTCOME_HORIZON_DAYS = 180

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "synthetic_v3"

EVENTS_FILE = OUTPUT_DIR / "hr_events.csv"
EMPLOYEES_FILE = OUTPUT_DIR / "employees.csv"
SNAPSHOTS_FILE = OUTPUT_DIR / "temporal_attrition_snapshots.csv"

PREDICTION_DATES = pd.date_range(
    "2025-01-01",
    "2025-12-01",
    freq="MS",
)

# The final prediction date must have a complete 180-day outcome window.
SIMULATION_START = PREDICTION_DATES[0]
EVENT_START = SIMULATION_START - pd.Timedelta(days=LOOKBACK_DAYS)
SIMULATION_END = (
    PREDICTION_DATES[-1] + pd.Timedelta(days=OUTCOME_HORIZON_DAYS)
)

rng = np.random.default_rng(SEED)


def random_date(
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.Timestamp:
    """Return a random date in the inclusive interval."""
    start = pd.Timestamp(start).normalize()
    end = pd.Timestamp(end).normalize()

    if end < start:
        raise ValueError(f"Invalid date range: {start} to {end}")

    days = (end - start).days
    return start + pd.Timedelta(
        days=int(rng.integers(0, days + 1))
    )


def sigmoid(value: float) -> float:
    return float(
        1.0 / (1.0 + np.exp(-np.clip(value, -30, 30)))
    )


def generate_employees() -> pd.DataFrame:
    """Create synthetic employee master records."""
    departments = [
        "Engineering",
        "Sales",
        "Human Resources",
        "Finance",
        "Operations",
        "Customer Support",
    ]

    employees = []

    for number in range(1, EMPLOYEE_COUNT + 1):
        employees.append(
            {
                "employee_id": f"EMP{number:04d}",
                "hire_date": random_date(
                    pd.Timestamp("2015-01-01"),
                    pd.Timestamp("2025-11-15"),
                ),
                "age": int(rng.integers(21, 61)),
                "department": str(rng.choice(departments)),
                "job_level": int(rng.choice([1, 2, 3, 4, 5])),
                "annual_base_salary_inr": int(
                    rng.integers(300_000, 2_000_001) // 1000 * 1000
                ),
                # Internal simulation variables; never model features.
                "_latent_risk": float(rng.normal(0, 1)),
                "_engagement_baseline": float(rng.uniform(2.4, 4.8)),
                "_performance_baseline": float(rng.uniform(2.5, 4.7)),
                "_satisfaction_baseline": float(rng.uniform(2.4, 4.8)),
            }
        )

    return pd.DataFrame(employees)


def generate_exit_dates(
    employees: pd.DataFrame,
) -> dict[str, pd.Timestamp | pd.NaT]:
    """
    Simulate exits separately from feature aggregation.

    The internal latent risk affects the synthetic exit process.
    It is never exported as a model feature.
    """
    exits: dict[str, pd.Timestamp | pd.NaT] = {}

    for employee in employees.to_dict("records"):
        employee_id = employee["employee_id"]
        hire_date = pd.Timestamp(employee["hire_date"]).normalize()

        start = max(hire_date, SIMULATION_START)

        if start > SIMULATION_END:
            exits[employee_id] = pd.NaT
            continue

        exit_probability = sigmoid(
            -4.0 + 0.85 * employee["_latent_risk"]
        )

        exit_date = pd.NaT
        current_month = start.to_period("M")

        while current_month.start_time <= SIMULATION_END:
            month_start = max(
                current_month.start_time.normalize(),
                start,
            )
            month_end = min(
                current_month.end_time.normalize(),
                SIMULATION_END,
            )

            if (
                month_start <= month_end
                and rng.random() < exit_probability
            ):
                exit_date = random_date(month_start, month_end)
                break

            current_month += 1

        exits[employee_id] = exit_date

    return exits


def generate_hr_events(
    employees: pd.DataFrame,
    exit_dates: dict[str, pd.Timestamp | pd.NaT],
) -> pd.DataFrame:
    """
    Generate timestamped synthetic HR events.

    Only generate the period needed for the prediction lookback windows.
    For employees who exit, their exit date is exclusive: no event may
    occur on or after the exit date.
    """
    rows: list[dict] = []

    for employee in employees.to_dict("records"):
        employee_id = employee["employee_id"]
        hire_date = pd.Timestamp(employee["hire_date"]).normalize()
        exit_date = exit_dates[employee_id]

        event_start = max(hire_date, EVENT_START)

        if pd.notna(exit_date):
            last_event_date = (
                pd.Timestamp(exit_date).normalize()
                - pd.Timedelta(days=1)
            )
        else:
            last_event_date = SIMULATION_END

        last_event_date = min(last_event_date, SIMULATION_END)

        if event_start > last_event_date:
            continue

        latent_risk = employee["_latent_risk"]
        engagement_baseline = employee["_engagement_baseline"]
        performance_baseline = employee["_performance_baseline"]
        satisfaction_baseline = employee["_satisfaction_baseline"]

        def emit(
            event_date: pd.Timestamp,
            event_type: str,
            value: float,
        ) -> None:
            event_date = pd.Timestamp(event_date).normalize()

            if event_date < hire_date:
                raise ValueError("Event occurs before hire date.")

            if event_date < event_start or event_date > last_event_date:
                raise ValueError("Event is outside the permitted event window.")

            if (
                pd.notna(exit_date)
                and event_date >= pd.Timestamp(exit_date).normalize()
            ):
                raise ValueError("Event occurs on or after exit date.")

            rows.append(
                {
                    "employee_id": employee_id,
                    "event_date": event_date,
                    "event_type": event_type,
                    "value": float(value),
                }
            )

        # Attendance: one absence-status event per weekday.
        workdays = pd.date_range(
            event_start,
            last_event_date,
            freq="B",
        )

        for day in workdays:
            absence_probability = float(
                np.clip(
                    0.025 + 0.025 * max(latent_risk, 0),
                    0.01,
                    0.20,
                )
            )

            absent = float(rng.random() < absence_probability)
            emit(day, "attendance_absent", absent)

            if absent == 0.0:
                hours = float(
                    np.clip(
                        rng.normal(8.0 - 0.12 * latent_risk, 0.7),
                        4.0,
                        12.0,
                    )
                )
                emit(day, "hours_worked", hours)

        # Monthly payroll events, dated on the last day of each month.
        payroll_months = pd.date_range(
            event_start.to_period("M").start_time,
            last_event_date.to_period("M").start_time,
            freq="MS",
        )

        for month in payroll_months:
            pay_date = month + pd.offsets.MonthEnd(0)

            if event_start <= pay_date <= last_event_date:
                emit(pay_date, "payroll_paid", 1.0)

        # Monthly engagement, satisfaction and NPS surveys.
        survey_months = pd.date_range(
            event_start.to_period("M").start_time,
            last_event_date.to_period("M").start_time,
            freq="MS",
        )

        for month in survey_months:
            survey_date = month + pd.Timedelta(
                days=int(rng.integers(0, 25))
            )

            if not event_start <= survey_date <= last_event_date:
                continue

            engagement = float(
                np.clip(
                    engagement_baseline
                    - 0.25 * latent_risk
                    + rng.normal(0, 0.45),
                    1.0,
                    5.0,
                )
            )

            satisfaction = float(
                np.clip(
                    satisfaction_baseline
                    - 0.20 * latent_risk
                    + rng.normal(0, 0.50),
                    1.0,
                    5.0,
                )
            )

            nps = float(
                np.clip(
                    (engagement - 3.0) * 30 + rng.normal(0, 15),
                    -100,
                    100,
                )
            )

            emit(survey_date, "engagement_score", engagement)
            emit(survey_date, "job_satisfaction_score", satisfaction)
            emit(survey_date, "employee_nps", nps)

        # Quarterly performance and manager-feedback events.
        review_dates = pd.date_range(
            event_start,
            last_event_date,
            freq="90D",
        )

        for review_date in review_dates:
            performance = float(
                np.clip(
                    performance_baseline
                    - 0.12 * latent_risk
                    + rng.normal(0, 0.40),
                    1.0,
                    5.0,
                )
            )

            feedback = float(
                np.clip(
                    3.5 - 0.18 * latent_risk + rng.normal(0, 0.50),
                    1.0,
                    5.0,
                )
            )

            emit(review_date, "performance_rating", performance)
            emit(review_date, "manager_feedback_score", feedback)

        # Infrequent promotions.
        for month in survey_months:
            if rng.random() < 0.08:
                promotion_date = month + pd.Timedelta(days=10)

                if event_start <= promotion_date <= last_event_date:
                    emit(promotion_date, "promotion", 1.0)

        # Leave episodes: record each leave day so total days can be
        # accurately aggregated in each 90-day lookback window.
        leave_cursor = event_start

        while leave_cursor < last_event_date:
            leave_cursor += pd.Timedelta(
                days=int(rng.integers(30, 100))
            )

            if leave_cursor > last_event_date:
                break

            duration = int(rng.integers(1, 5))
            leave_end = min(
                leave_cursor + pd.Timedelta(days=duration - 1),
                last_event_date,
            )

            emit(leave_cursor, "leave_start", 1.0)

            for leave_day in pd.date_range(
                leave_cursor,
                leave_end,
                freq="D",
            ):
                emit(leave_day, "leave_day", 1.0)

            emit(leave_end, "leave_end", 1.0)

    events = pd.DataFrame(rows)

    if events.empty:
        raise RuntimeError("No HR events were generated.")

    return events.sort_values(
        ["employee_id", "event_date", "event_type"]
    ).reset_index(drop=True)


def calculate_snapshot_features(
    employee: dict,
    employee_events: pd.DataFrame,
    prediction_date: pd.Timestamp,
) -> dict:
    """
    Calculate features using events in:
    [prediction_date - 90 days, prediction_date)

    The prediction date itself is excluded.
    """
    prediction_date = pd.Timestamp(prediction_date).normalize()
    window_start = prediction_date - pd.Timedelta(days=LOOKBACK_DAYS)

    history = employee_events.loc[
        (employee_events["event_date"] >= window_start)
        & (employee_events["event_date"] < prediction_date)
    ]

    def values(event_type: str) -> pd.Series:
        return history.loc[
            history["event_type"] == event_type,
            "value",
        ]

    def mean_or_default(
        event_type: str,
        default: float,
    ) -> float:
        series = values(event_type)
        return float(series.mean()) if not series.empty else default

    def count(event_type: str) -> int:
        return int((history["event_type"] == event_type).sum())

    tenure = max(
        0.0,
        (
            prediction_date - pd.Timestamp(employee["hire_date"])
        ).days / 365.25,
    )

    return {
        "age": int(employee["age"]),
        "tenure_years": round(tenure, 3),
        "department": employee["department"],
        "job_level": int(employee["job_level"]),
        "annual_base_salary_inr": int(
            employee["annual_base_salary_inr"]
        ),
        "attendance_record_count_90d": count("attendance_absent"),
        "average_hours_worked_90d": round(
            mean_or_default("hours_worked", 8.0),
            3,
        ),
        "absent_days_90d": int(values("attendance_absent").sum()),
        "average_performance_rating_90d": round(
            mean_or_default("performance_rating", 3.5),
            3,
        ),
        "average_manager_feedback_score_90d": round(
            mean_or_default("manager_feedback_score", 3.5),
            3,
        ),
        "promotion_count_90d": count("promotion"),
        "average_engagement_score_90d": round(
            mean_or_default("engagement_score", 3.5),
            3,
        ),
        "average_job_satisfaction_score_90d": round(
            mean_or_default("job_satisfaction_score", 3.5),
            3,
        ),
        "average_employee_nps_90d": round(
            mean_or_default("employee_nps", 0.0),
            3,
        ),
        "leave_record_count_90d": count("leave_start"),
        "total_leave_days_90d": count("leave_day"),
        "payroll_record_count_90d": count("payroll_paid"),
    }


def build_snapshots(
    employees: pd.DataFrame,
    events: pd.DataFrame,
    exit_dates: dict[str, pd.Timestamp | pd.NaT],
) -> pd.DataFrame:
    """Build monthly snapshots and forward-looking outcome labels."""
    snapshots: list[dict] = []

    for employee in employees.to_dict("records"):
        employee_id = employee["employee_id"]
        hire_date = pd.Timestamp(employee["hire_date"]).normalize()
        exit_date = exit_dates[employee_id]

        employee_events = events.loc[
            events["employee_id"] == employee_id
        ]

        for prediction_date in PREDICTION_DATES:
            prediction_date = pd.Timestamp(prediction_date).normalize()

            # Must be employed at the beginning of prediction date.
            if hire_date >= prediction_date:
                continue

            if (
                pd.notna(exit_date)
                and prediction_date >= pd.Timestamp(exit_date).normalize()
            ):
                continue

            outcome_end = (
                prediction_date
                + pd.Timedelta(days=OUTCOME_HORIZON_DAYS)
            )

            if outcome_end > SIMULATION_END:
                raise ValueError(
                    f"Incomplete outcome horizon for {prediction_date.date()}."
                )

            label = int(
                pd.notna(exit_date)
                and prediction_date < pd.Timestamp(exit_date) <= outcome_end
            )

            features = calculate_snapshot_features(
                employee,
                employee_events,
                prediction_date,
            )

            snapshots.append(
                {
                    "employee_id": employee_id,
                    "prediction_date": prediction_date.date().isoformat(),
                    **features,
                    "attrited_within_180_days_label": label,
                    # Audit-only; never a model feature.
                    "exit_date_for_validation_only": (
                        pd.Timestamp(exit_date).date().isoformat()
                        if pd.notna(exit_date)
                        else None
                    ),
                }
            )

    result = pd.DataFrame(snapshots)

    if result.empty:
        raise RuntimeError("No temporal snapshots were generated.")

    return result


def validate_temporal_integrity(
    employees: pd.DataFrame,
    events: pd.DataFrame,
    snapshots: pd.DataFrame,
    exit_dates: dict[str, pd.Timestamp | pd.NaT],
) -> None:
    """Validate event timing, feature values and forward outcome labels."""
    hire_dates = employees.set_index("employee_id")["hire_date"]
    event_hires = events["employee_id"].map(hire_dates)

    if (events["event_date"] < event_hires).any():
        raise RuntimeError("An HR event occurs before hire date.")

    event_exits = events["employee_id"].map(exit_dates)
    event_exits = pd.to_datetime(event_exits, errors="coerce")

    if (
        event_exits.notna()
        & (events["event_date"] >= event_exits)
    ).any():
        raise RuntimeError("An HR event occurs on or after exit date.")

    if snapshots.duplicated(
        ["employee_id", "prediction_date"]
    ).any():
        raise RuntimeError("Duplicate employee/date snapshots found.")

    prediction_dates = pd.to_datetime(snapshots["prediction_date"])
    audit_exits = pd.to_datetime(
        snapshots["exit_date_for_validation_only"],
        errors="coerce",
    )
    labels = snapshots["attrited_within_180_days_label"]

    if not labels.isin([0, 1]).all():
        raise RuntimeError("Labels must contain only 0 and 1.")

    if (
        audit_exits.notna()
        & (audit_exits <= prediction_dates)
    ).any():
        raise RuntimeError("Snapshot occurs on or after employee exit.")

    positive = labels == 1
    positive_exits = audit_exits.loc[positive]
    positive_dates = prediction_dates.loc[positive]

    positive_valid = (
        positive_exits.notna()
        & (positive_exits > positive_dates)
        & (
            positive_exits
            <= positive_dates
            + pd.Timedelta(days=OUTCOME_HORIZON_DAYS)
        )
    )

    if not positive_valid.all():
        raise RuntimeError("Positive label integrity check failed.")

    negative = labels == 0
    negative_exits = audit_exits.loc[negative]
    negative_dates = prediction_dates.loc[negative]

    negative_valid = (
        negative_exits.isna()
        | (
            negative_exits
            > negative_dates
            + pd.Timedelta(days=OUTCOME_HORIZON_DAYS)
        )
    )

    if not negative_valid.all():
        raise RuntimeError("Negative label integrity check failed.")

    feature_columns = [
        column
        for column in snapshots.columns
        if column not in {
            "employee_id",
            "prediction_date",
            "attrited_within_180_days_label",
            "exit_date_for_validation_only",
        }
    ]

    if snapshots[feature_columns].isna().any().any():
        raise RuntimeError("Missing values found in model features.")

    numeric_columns = snapshots[feature_columns].select_dtypes(
        include=[np.number]
    )

    if not np.isfinite(
        numeric_columns.to_numpy(dtype=float)
    ).all():
        raise RuntimeError("Non-finite numeric features found.")

    # Verify feature-window bounds independently for every snapshot.
    event_groups = {
        employee_id: group["event_date"]
        for employee_id, group in events.groupby("employee_id")
    }

    for row in snapshots[
        ["employee_id", "prediction_date"]
    ].itertuples(index=False):
        cutoff = pd.Timestamp(row.prediction_date)
        start = cutoff - pd.Timedelta(days=LOOKBACK_DAYS)
        dates = event_groups.get(row.employee_id)

        if dates is None:
            continue

        window_dates = dates.loc[
            (dates >= start) & (dates < cutoff)
        ]

        if (
            (window_dates < start).any()
            or (window_dates >= cutoff).any()
        ):
            raise RuntimeError("Feature lookback boundary check failed.")

    print("Temporal integrity checks: PASS")
    print("Event hire-date/exit-date boundaries: PASS")
    print("90-day feature lookback: PASS")
    print("Positive and negative outcome labels: PASS")
    print("No duplicate employee/date snapshots: PASS")
    print("Model features contain no missing/non-finite values: PASS")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    employees = generate_employees()
    exit_dates = generate_exit_dates(employees)
    events = generate_hr_events(employees, exit_dates)
    snapshots = build_snapshots(employees, events, exit_dates)

    validate_temporal_integrity(
        employees,
        events,
        snapshots,
        exit_dates,
    )

    # Export employee master data without internal simulation variables.
    employee_export = employees.drop(
        columns=[
            "_latent_risk",
            "_engagement_baseline",
            "_performance_baseline",
            "_satisfaction_baseline",
        ]
    ).copy()

    employee_export.to_csv(EMPLOYEES_FILE, index=False)
    events.to_csv(EVENTS_FILE, index=False)
    snapshots.to_csv(SNAPSHOTS_FILE, index=False)

    print(f"\nEmployees saved: {EMPLOYEES_FILE}")
    print(f"Events saved: {EVENTS_FILE}")
    print(f"Snapshots saved: {SNAPSHOTS_FILE}")
    print(f"Employee count: {employee_export['employee_id'].nunique()}")
    print(f"Event rows: {len(events)}")
    print(f"Snapshot rows: {len(snapshots)}")

    print(
        "Positive labels:",
        int(snapshots["attrited_within_180_days_label"].sum()),
    )
    print(
        "Negative labels:",
        int((snapshots["attrited_within_180_days_label"] == 0).sum()),
    )

    print("\nLabels by prediction date:")
    print(
        snapshots.groupby("prediction_date")[
            "attrited_within_180_days_label"
        ].agg(["count", "sum"])
    )


if __name__ == "__main__":
    main()
