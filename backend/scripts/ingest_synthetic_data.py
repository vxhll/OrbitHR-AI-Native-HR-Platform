from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.db.database import SessionLocal
from app.models import Organization, Department, Employee
from app.models.attrition_record import AttritionRecord
from app.models.attendance_login import AttendanceLogin
from app.models.payroll import Payroll
from app.models.performance_review import PerformanceReview
from app.models.engagement_survey import EngagementSurvey
from app.models.leave_record import LeaveRecord


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "synthetic"


def clean_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def load_csv(filename):
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    print(f"Reading {filename}...")
    return pd.read_csv(path)


def main():
    print("=" * 60)
    print("OrbitHR Synthetic Data Ingestion")
    print("=" * 60)
    print(f"Data directory: {DATA_DIR}")
    print()

    # ---------------------------------------------------------
    # Load CSV files
    # ---------------------------------------------------------

    employee_df = load_csv("01_employee_master.csv")
    attrition_df = load_csv("02_attrition_records.csv")
    attendance_df = load_csv("03_daily_attendance_login.csv")
    payroll_df = load_csv("04_monthly_payroll.csv")
    performance_df = load_csv("05_performance_reviews.csv")
    engagement_df = load_csv("06_engagement_surveys.csv")
    leave_df = load_csv("07_leave_records.csv")

    print()
    print("CSV files loaded successfully.")
    print()

    db = SessionLocal()

    try:
        # -----------------------------------------------------
        # 1. ORGANIZATION
        # -----------------------------------------------------

        organization = db.scalar(
            select(Organization).where(
                Organization.name == "OrbitHR Demo Organization"
            )
        )

        if organization is None:
            organization = Organization(
                name="OrbitHR Demo Organization"
            )
            db.add(organization)
            db.flush()

        organization_id = organization.id

        print(f"Organization ready: {organization.name}")

        # -----------------------------------------------------
        # 2. DEPARTMENTS
        # -----------------------------------------------------

        department_names = sorted(
            employee_df["department"].dropna().unique().tolist()
        )

        department_map = {}

        for department_name in department_names:
            department = db.scalar(
                select(Department).where(
                    Department.name == department_name,
                    Department.organization_id == organization_id,
                )
            )

            if department is None:
                department = Department(
                    name=department_name,
                    organization_id=organization_id,
                )
                db.add(department)
                db.flush()

            department_map[department_name] = department.id

        print(f"Departments ready: {len(department_map)}")

        # -----------------------------------------------------
        # 3. EMPLOYEES
        # -----------------------------------------------------

        existing_employees = {
            employee.employee_id: employee
            for employee in db.scalars(select(Employee)).all()
        }

        # First insert employees without manager_id.
        # Manager references are resolved afterward.
        employee_map = {}

        for _, row in employee_df.iterrows():
            employee_id = row["employee_id"]

            if employee_id in existing_employees:
                employee = existing_employees[employee_id]
            else:
                employee = Employee(
                    employee_id=employee_id,
                    full_name=row["full_name"],
                    gender=row["gender"],
                    age=int(row["age"]),
                    department_id=department_map[row["department"]],
                    job_role=row["job_role"],
                    job_level=row["job_level"],
                    work_location=row["work_location"],
                    hire_date=pd.to_datetime(
                        row["hire_date"]
                    ).date(),
                    tenure_years_at_period_start=float(
                        row["tenure_years_at_period_start"]
                    ),
                    education=row["education"],
                    marital_status=row["marital_status"],
                    annual_base_salary_inr=int(
                        row["annual_base_salary_inr"]
                    ),
                    manager_id=None,
                )

                db.add(employee)
                db.flush()

            employee_map[employee_id] = employee

        # Resolve manager relationships after every employee exists.
        for _, row in employee_df.iterrows():
            employee_id = row["employee_id"]
            manager_id = clean_value(row["manager_id"])

            employee = employee_map[employee_id]

            if manager_id and manager_id in employee_map:
                employee.manager_id = manager_id
            else:
                employee.manager_id = None

        db.flush()

        print(f"Employees ready: {len(employee_map)}")

        # -----------------------------------------------------
        # 4. ATTRITION RECORDS
        # -----------------------------------------------------

        existing_attrition = {
            record.employee_id: record
            for record in db.scalars(
                select(AttritionRecord)
            ).all()
        }

        for _, row in attrition_df.iterrows():
            employee_id = row["employee_id"]

            values = {
                "employee_id": employee_id,
                "employment_status": row["employment_status"],
                "exit_date": (
                    pd.to_datetime(row["exit_date"]).date()
                    if clean_value(row["exit_date"])
                    else None
                ),
                "exit_type": clean_value(row["exit_type"]),
                "exit_reason": clean_value(row["exit_reason"]),
                "notice_period_days": (
                    int(row["notice_period_days"])
                    if clean_value(row["notice_period_days"])
                    else None
                ),
                "rehire_eligible": (
                    str(row["rehire_eligible"]).lower() == "yes"
                    if clean_value(row["rehire_eligible"])
                    else None
                ),
                "attrited_within_180_days_label": int(
                    row["attrited_within_180_days_label"]
                ),
            }

            if employee_id in existing_attrition:
                record = existing_attrition[employee_id]

                for key, value in values.items():
                    setattr(record, key, value)
            else:
                db.add(AttritionRecord(**values))

        db.flush()

        print(f"Attrition records ready: {len(attrition_df)}")

        # -----------------------------------------------------
        # 5. ATTENDANCE / LOGIN
        # -----------------------------------------------------

        attendance_count = 0

        for _, row in attendance_df.iterrows():
            record = AttendanceLogin(
                employee_id=row["employee_id"],
                date=pd.to_datetime(row["date"]).date(),
                status=row["status"],
                login_time=(
                    pd.to_datetime(
                        row["login_time"]
                    ).time()
                    if clean_value(row["login_time"])
                    else None
                ),
                logout_time=(
                    pd.to_datetime(
                        row["logout_time"]
                    ).time()
                    if clean_value(row["logout_time"])
                    else None
                ),
                hours_worked=(
                    float(row["hours_worked"])
                    if clean_value(row["hours_worked"])
                    else None
                ),
            )

            db.add(record)
            attendance_count += 1

            if attendance_count % 5000 == 0:
                db.flush()
                print(
                    f"  Attendance records processed: "
                    f"{attendance_count}"
                )

        db.flush()

        print(
            f"Attendance records ready: "
            f"{attendance_count}"
        )

        # -----------------------------------------------------
        # 6. PAYROLL
        # -----------------------------------------------------

        payroll_count = 0

        for _, row in payroll_df.iterrows():
            record = Payroll(
                employee_id=row["employee_id"],
                pay_month=row["pay_month"],
                base_pay_inr=int(row["base_pay_inr"]),
                bonus_inr=int(row["bonus_inr"]),
                deductions_inr=int(row["deductions_inr"]),
                net_pay_inr=int(row["net_pay_inr"]),
                payment_date=pd.to_datetime(
                    row["payment_date"]
                ).date(),
            )

            db.add(record)
            payroll_count += 1

        db.flush()

        print(f"Payroll records ready: {payroll_count}")

        # -----------------------------------------------------
        # 7. PERFORMANCE REVIEWS
        # -----------------------------------------------------

        performance_count = 0

        for _, row in performance_df.iterrows():
            record = PerformanceReview(
                employee_id=row["employee_id"],
                review_period=row["review_period"],
                performance_rating_1to5=float(
                    row["performance_rating_1to5"]
                ),
                manager_feedback_score_1to10=float(
                    row["manager_feedback_score_1to10"]
                ),
                promotion_flag=(
                    str(row["promotion_flag"]).lower() == "yes"
                ),
            )

            db.add(record)
            performance_count += 1

        db.flush()

        print(
            f"Performance records ready: "
            f"{performance_count}"
        )

        # -----------------------------------------------------
        # 8. ENGAGEMENT SURVEYS
        # -----------------------------------------------------

        engagement_count = 0

        for _, row in engagement_df.iterrows():
            record = EngagementSurvey(
                employee_id=row["employee_id"],
                survey_period=row["survey_month"],
                engagement_score_1to10=float(
                    row["engagement_score_1to10"]
                ),
                job_satisfaction_score_1to10=float(
                    row["job_satisfaction_score_1to10"]
                ),
                employee_nps=int(row["employee_nps"]),
            )

            db.add(record)
            engagement_count += 1

        db.flush()

        print(
            f"Engagement records ready: "
            f"{engagement_count}"
        )

        # -----------------------------------------------------
        # 9. LEAVE RECORDS
        # -----------------------------------------------------

        leave_count = 0

        for _, row in leave_df.iterrows():
            record = LeaveRecord(
                employee_id=row["employee_id"],
                leave_type=row["leave_type"],
                start_date=pd.to_datetime(
                    row["start_date"]
                ).date(),
                end_date=pd.to_datetime(
                    row["end_date"]
                ).date(),
                days=int(row["days"]),
                approval_status=row["approval_status"],
                approved_by=clean_value(row["approved_by"]),
            )

            db.add(record)
            leave_count += 1

        db.flush()

        print(f"Leave records ready: {leave_count}")

        # -----------------------------------------------------
        # COMMIT
        # -----------------------------------------------------

        db.commit()

        print()
        print("=" * 60)
        print("INGESTION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print()
        print(f"Employees:     {len(employee_df)}")
        print(f"Attrition:     {len(attrition_df)}")
        print(f"Attendance:    {len(attendance_df)}")
        print(f"Payroll:       {len(payroll_df)}")
        print(f"Performance:   {len(performance_df)}")
        print(f"Engagement:    {len(engagement_df)}")
        print(f"Leave:         {len(leave_df)}")
        print()

    except Exception:
        db.rollback()
        print()
        print("=" * 60)
        print("INGESTION FAILED — DATABASE ROLLED BACK")
        print("=" * 60)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()