
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "synthetic_v3"

EMPLOYEES_PATH = DATA_DIR / "employees.csv"
EVENTS_PATH = DATA_DIR / "hr_events.csv"
SNAPSHOTS_PATH = DATA_DIR / "temporal_attrition_snapshots.csv"

LABEL_COL = "attrited_within_180_days_label"
AUDIT_COL = "exit_date_for_validation_only"

LOOKBACK_DAYS = 90
OUTCOME_HORIZON_DAYS = 180
SIMULATION_END = pd.Timestamp("2026-05-30")

FEATURE_COLS = [
    "age",
    "tenure_years",
    "department",
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

EMPLOYEE_COLUMNS = {
    "employee_id",
    "hire_date",
    "age",
    "department",
    "job_level",
    "annual_base_salary_inr",
}

EVENT_COLUMNS = {
    "employee_id",
    "event_date",
    "event_type",
    "value",
}

SNAPSHOT_COLUMNS = {
    "employee_id",
    "prediction_date",
    LABEL_COL,
    AUDIT_COL,
    *FEATURE_COLS,
}


# ============================================================
# LOAD DATA
# ============================================================

def load_data():
    for path in [
        EMPLOYEES_PATH,
        EVENTS_PATH,
        SNAPSHOTS_PATH,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required dataset file not found: {path}"
            )

    employees = pd.read_csv(
        EMPLOYEES_PATH,
        parse_dates=["hire_date"],
    )

    events = pd.read_csv(
        EVENTS_PATH,
        parse_dates=["event_date"],
    )

    snapshots = pd.read_csv(
        SNAPSHOTS_PATH,
        parse_dates=["prediction_date"],
    )

    snapshots[AUDIT_COL] = pd.to_datetime(
        snapshots[AUDIT_COL],
        errors="coerce",
    )

    return employees, events, snapshots


# ============================================================
# HELPERS
# ============================================================

def check_required_columns(df, required, dataset_name):
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"{dataset_name} is missing columns: "
            f"{sorted(missing)}"
        )


def numeric_values(series):
    return pd.to_numeric(series, errors="coerce").dropna()


def event_values(window, event_type):
    selected = window.loc[
        window["event_type"] == event_type,
        "value",
    ]

    return numeric_values(selected)


def event_count(window, event_type):
    return int((window["event_type"] == event_type).sum())


def event_mean(window, event_type, default):
    values = event_values(window, event_type)

    if values.empty:
        return float(default)

    return float(values.mean())


def event_sum(window, event_type):
    values = event_values(window, event_type)

    if values.empty:
        return 0.0

    return float(values.sum())


# ============================================================
# INDEPENDENT FEATURE RECOMPUTATION
# ============================================================

def recompute_features(employee, employee_events, prediction_date):
    """
    Recompute the snapshot features directly from employee
    attributes and raw HR events.

    Feature window:
        prediction_date - 90 days <= event_date < prediction_date
    """

    cutoff = prediction_date - pd.Timedelta(
        days=LOOKBACK_DAYS
    )

    window = employee_events.loc[
        (employee_events["event_date"] >= cutoff)
        & (employee_events["event_date"] < prediction_date)
    ]

    tenure_days = (
        prediction_date - employee["hire_date"]
    ).days

    tenure_years = tenure_days / 365.25

    return {
        "age": float(employee["age"]),
        "tenure_years": tenure_years,
        "department": str(employee["department"]),
        "job_level": float(employee["job_level"]),
        "annual_base_salary_inr": float(
            employee["annual_base_salary_inr"]
        ),

        "attendance_record_count_90d": event_count(
            window, "attendance_absent"
        ),

        "average_hours_worked_90d": event_mean(
            window, "hours_worked", 8.0
        ),

        "absent_days_90d": event_sum(
            window, "attendance_absent"
        ),

        "average_performance_rating_90d": event_mean(
            window, "performance_rating", 3.5
        ),

        "average_manager_feedback_score_90d": event_mean(
            window, "manager_feedback_score", 3.5
        ),

        "promotion_count_90d": event_count(
            window, "promotion"
        ),

        "average_engagement_score_90d": event_mean(
            window, "engagement_score", 3.5
        ),

        "average_job_satisfaction_score_90d": event_mean(
            window, "job_satisfaction_score", 3.5
        ),

        "average_employee_nps_90d": event_mean(
            window, "employee_nps", 0.0
        ),

        "leave_record_count_90d": event_count(
            window, "leave_start"
        ),

        "total_leave_days_90d": event_count(
            window, "leave_day"
        ),

        "payroll_record_count_90d": event_count(
            window, "payroll_paid"
        ),
    }


# ============================================================
# VALIDATION
# ============================================================

def main():
    employees, events, snapshots = load_data()

    check_required_columns(
        employees, EMPLOYEE_COLUMNS, "employees.csv"
    )

    check_required_columns(
        events, EVENT_COLUMNS, "hr_events.csv"
    )

    check_required_columns(
        snapshots, SNAPSHOT_COLUMNS,
        "temporal_attrition_snapshots.csv"
    )

    employees["employee_id"] = (
        employees["employee_id"].astype(str)
    )
    events["employee_id"] = events["employee_id"].astype(str)
    snapshots["employee_id"] = (
        snapshots["employee_id"].astype(str)
    )

    checks = {}

    # --------------------------------------------------------
    # Basic dataset integrity
    # --------------------------------------------------------

    checks["Employee IDs are unique"] = (
        employees["employee_id"].is_unique
    )

    checks["No duplicate employee/date snapshots"] = (
        not snapshots.duplicated(
            ["employee_id", "prediction_date"]
        ).any()
    )

    checks["All snapshot employees exist"] = (
        snapshots["employee_id"].isin(
            employees["employee_id"]
        ).all()
    )

    checks["All event employees exist"] = (
        events["employee_id"].isin(
            employees["employee_id"]
        ).all()
    )

    checks["No missing snapshot model features"] = (
        not snapshots[FEATURE_COLS].isna().any().any()
    )

    numeric_features = snapshots[
        FEATURE_COLS
    ].select_dtypes(include=[np.number])

    checks["All numeric model features are finite"] = (
        np.isfinite(
            numeric_features.to_numpy(dtype=float)
        ).all()
    )

    checks["Prediction dates are valid"] = (
        snapshots["prediction_date"].notna().all()
    )

    checks["Event dates are valid"] = (
        events["event_date"].notna().all()
    )

    checks["Hire dates are valid"] = (
        employees["hire_date"].notna().all()
    )

    checks["Snapshot labels are binary"] = (
        snapshots[LABEL_COL].notna().all()
        and set(snapshots[LABEL_COL].unique()).issubset(
            {0, 1}
        )
    )

    checks["Both label classes are present"] = (
        snapshots[LABEL_COL].nunique() == 2
    )

    # --------------------------------------------------------
    # Feature schema and leakage exclusions
    # --------------------------------------------------------

    excluded_columns = {
        "employee_id",
        "prediction_date",
        LABEL_COL,
        AUDIT_COL,
    }

    actual_features = [
        column for column in snapshots.columns
        if column not in excluded_columns
    ]

    checks["Model feature schema matches expected features"] = (
        set(actual_features) == set(FEATURE_COLS)
    )

    checks["Label and audit fields excluded from features"] = (
        LABEL_COL not in actual_features
        and AUDIT_COL not in actual_features
        and "employee_id" not in actual_features
        and "prediction_date" not in actual_features
    )

    # --------------------------------------------------------
    # Employee / event date boundaries
    # --------------------------------------------------------

    employee_lookup = employees.set_index("employee_id")
    hire_lookup = employee_lookup["hire_date"]

    event_hire_dates = events["employee_id"].map(
        hire_lookup
    )

    checks["Events occur on or after hire dates"] = (
        (events["event_date"] >= event_hire_dates).all()
    )

    # Recover each employee's exit date from the audit column.
    exit_counts = snapshots.groupby("employee_id")[
        AUDIT_COL
    ].nunique(dropna=True)

    checks["Exit dates are consistent per employee"] = (
        (exit_counts <= 1).all()
    )

    exit_lookup = (
        snapshots.dropna(subset=[AUDIT_COL])
        .groupby("employee_id")[AUDIT_COL]
        .first()
    )

    event_exit_dates = events["employee_id"].map(
        exit_lookup
    )

    events_with_exit = event_exit_dates.notna()

    checks["Events occur strictly before known exits"] = (
        (
            events.loc[events_with_exit, "event_date"].to_numpy()
            < event_exit_dates.loc[events_with_exit].to_numpy()
        ).all()
    )

    snapshot_exit_dates = snapshots[AUDIT_COL]
    prediction_dates = snapshots["prediction_date"]

    checks["Snapshots occur before known exits"] = (
        snapshot_exit_dates.isna()
        | (prediction_dates < snapshot_exit_dates)
    ).all()

    # --------------------------------------------------------
    # Label / outcome window validation
    # --------------------------------------------------------

    outcome_end = (
        prediction_dates
        + pd.Timedelta(days=OUTCOME_HORIZON_DAYS)
    )

    labels = snapshots[LABEL_COL]
    exits = snapshot_exit_dates

    positive_valid = (
        (labels == 1)
        & exits.notna()
        & (exits > prediction_dates)
        & (exits <= outcome_end)
    )

    negative_valid = (
        (labels == 0)
        & (
            exits.isna()
            | (exits > outcome_end)
        )
    )

    checks["Positive labels match 180-day exit window"] = (
        ((labels == 1) == positive_valid).all()
    )

    checks["Negative labels have complete outcome windows"] = (
        ((labels == 0) == negative_valid).all()
    )

    checks["All outcome windows are fully observable"] = (
        (outcome_end <= SIMULATION_END).all()
    )

    # --------------------------------------------------------
    # Independent 90-day feature verification
    # --------------------------------------------------------

    events_by_employee = {
        employee_id: group.sort_values("event_date")
        for employee_id, group in events.groupby(
            "employee_id", sort=False
        )
    }

    employee_records = employees.set_index(
        "employee_id"
    ).to_dict("index")

    feature_mismatches = []
    checked_snapshots = 0

    for row in snapshots.itertuples(index=False):
        employee_id = str(row.employee_id)
        prediction_date = pd.Timestamp(row.prediction_date)

        employee = employee_records.get(employee_id)

        if employee is None:
            continue

        employee_events = events_by_employee.get(
            employee_id,
            events.iloc[0:0],
        )

        recomputed = recompute_features(
            employee,
            employee_events,
            prediction_date,
        )

        checked_snapshots += 1


        for feature in FEATURE_COLS:
            actual = getattr(row, feature)
            expected = recomputed[feature]

            if feature == "department":
                matches = str(actual) == str(expected)
            else:
                matches = np.isclose(
                    float(actual),
                    float(expected),
                    rtol=1e-5,
                    atol=(
                        0.011
                        if feature == "tenure_years"
                        else 0.00051
                    ),
                )

            if not matches:
                feature_mismatches.append(
                    {
                        "employee_id": employee_id,
                        "prediction_date": str(
                            prediction_date.date()
                        ),
                        "feature": feature,
                        "dataset_value": actual,
                        "recomputed_value": expected,
                    }
                )

    checks["All snapshots independently feature-checked"] = (
        checked_snapshots == len(snapshots)
    )

    checks["90-day features match raw HR events"] = (
        len(feature_mismatches) == 0
        and checked_snapshots == len(snapshots)
    )


    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    print("\n=== ORBITHR V3 DATASET VALIDATION ===")
    print(f"Employees: {len(employees):,}")
    print(f"HR event rows: {len(events):,}")
    print(f"Prediction snapshots: {len(snapshots):,}")
    print(
        "Unique employees in snapshots:",
        snapshots["employee_id"].nunique(),
    )
    print(
        "Prediction date range:",
        snapshots["prediction_date"].min(),
        "to",
        snapshots["prediction_date"].max(),
    )

    print("\n=== VALIDATION CHECKS ===")

    for description, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {description}")

    print("\n=== LABEL DISTRIBUTION ===")
    print(
        snapshots[LABEL_COL]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print(
        "\nPositive-label rate:",
        f"{snapshots[LABEL_COL].mean() * 100:.2f}%",
    )

    print("\n=== MODEL FEATURES ===")
    for feature in FEATURE_COLS:
        print(f"- {feature}")

    if feature_mismatches:
        print("\n=== FEATURE MISMATCH EXAMPLES ===")

        for mismatch in feature_mismatches[:10]:
            print(mismatch)

    failed = [
        name for name, passed in checks.items()
        if not passed
    ]

    if failed:
        print("\nVALIDATION FAILED")

        for name in failed:
            print(f"- {name}")

        raise SystemExit(1)

    print("\nALL INDEPENDENT V3 CHECKS PASSED")


if __name__ == "__main__":
    main()
