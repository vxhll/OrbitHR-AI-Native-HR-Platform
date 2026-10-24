
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, UTC, timedelta
from threading import Barrier
from uuid import uuid4

from sqlalchemy import delete, select

from app.db.database import SessionLocal, DATABASE_URL
from app.models.organization import Organization
from app.models.department import Department
from app.models.employee import Employee
from app.models.onboarding.case import OnboardingCase
from app.models.onboarding.task import OnboardingTask
from app.models.onboarding.reminder import OnboardingReminder
from app.services.onboarding_reminder_service import _claim_reminder
from sqlalchemy.engine import make_url


def utcnow_naive():
    return datetime.now(UTC).replace(tzinfo=None)


def main():
    target = make_url(DATABASE_URL)
    if target.database != "orbithr_test_db":
        raise RuntimeError(
            f"Safety stop: expected orbithr_test_db, got {target.database!r}"
        )

    suffix = uuid4().hex[:12]
    employee_code = f"RT{suffix}"
    organization_id = department_id = case_id = task_id = None

    setup_db = SessionLocal()
    try:
        organization = Organization(name=f"Retry Test {suffix}")
        setup_db.add(organization)
        setup_db.flush()

        department = Department(
            name=f"Retry {suffix}",
            organization_id=organization.id,
        )
        setup_db.add(department)
        setup_db.flush()

        employee = Employee(
            employee_id=employee_code,
            full_name="Retry Concurrency Test",
            gender="Not Specified",
            age=30,
            department_id=department.id,
            job_role="Test Engineer",
            job_level="Test",
            work_location="Test",
            hire_date=date.today(),
            tenure_years_at_period_start=0,
            education="Test",
            marital_status="Not Specified",
            annual_base_salary_inr=100000,
        )
        setup_db.add(employee)
        setup_db.flush()

        onboarding_case = OnboardingCase(
            employee_id=employee_code,
            status="In Progress",
            joining_date=date.today(),
            completion_percentage=0,
        )
        setup_db.add(onboarding_case)
        setup_db.flush()

        task = OnboardingTask(
            onboarding_case_id=onboarding_case.id,
            task_code=f"RETRY_{suffix}",
            title="Retry concurrency test task",
            category="Testing",
            required=True,
            status="Pending",
            due_date=date.today(),
        )
        setup_db.add(task)
        setup_db.flush()

        organization_id = organization.id
        department_id = department.id
        case_id = onboarding_case.id
        task_id = task.id

        now = utcnow_naive()
        reminder_date = datetime.combine(date.today(), time.min)

        reminder = OnboardingReminder(
            task_id=task_id,
            recipient_email="retry-test@example.invalid",
            reminder_type="OVERDUE_DAILY",
            reminder_date=reminder_date,
            status="Failed",
            attempts=1,
            last_attempt_at=now - timedelta(minutes=20),
            created_at=now,
            error_message="Simulated previous failure",
        )
        setup_db.add(reminder)
        setup_db.commit()

        candidate = {
            "task_id": task_id,
            "recipient_email": "retry-test@example.invalid",
            "reminder_type": "OVERDUE_DAILY",
        }

        start_barrier = Barrier(2)

        def attempt_retry():
            db = SessionLocal()
            try:
                start_barrier.wait(timeout=10)
                return _claim_reminder(
                    db,
                    candidate,
                    reminder_date,
                    utcnow_naive(),
                )
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(attempt_retry),
                executor.submit(attempt_retry),
            ]
            results = [future.result(timeout=30) for future in futures]

        winners = [r for r in results if isinstance(r, tuple)]
        non_winners = [r for r in results if isinstance(r, dict)]

        print("Database:", target.database)
        print("Retry results:", results)
        print("Successful retry claims:", len(winners))
        print("Non-winning outcomes:", non_winners)

        if len(winners) != 1:
            raise AssertionError(
                f"Expected exactly one retry winner, got {len(winners)}"
            )

        with SessionLocal() as verify_db:
            saved = verify_db.execute(
                select(OnboardingReminder).where(
                    OnboardingReminder.task_id == task_id,
                    OnboardingReminder.reminder_type == "OVERDUE_DAILY",
                    OnboardingReminder.reminder_date == reminder_date,
                )
            ).scalar_one()

            print("Persisted status:", saved.status)
            print("Persisted attempts:", saved.attempts)
            print("Persisted claim token:", "present" if saved.claim_token else "missing")

            if saved.status != "Sending":
                raise AssertionError(f"Expected Sending, got {saved.status!r}")
            if saved.attempts != 2:
                raise AssertionError(f"Expected attempts=2, got {saved.attempts}")
            if not saved.claim_token:
                raise AssertionError("Expected a persisted claim token")

        print("PASS: only one worker acquired the retry claim")

    finally:
        setup_db.rollback()
        if task_id is not None:
            setup_db.execute(
                delete(OnboardingReminder).where(
                    OnboardingReminder.task_id == task_id
                )
            )
            setup_db.execute(
                delete(OnboardingTask).where(OnboardingTask.id == task_id)
            )
        if case_id is not None:
            setup_db.execute(
                delete(OnboardingCase).where(OnboardingCase.id == case_id)
            )
        setup_db.execute(
            delete(Employee).where(Employee.employee_id == employee_code)
        )
        if department_id is not None:
            setup_db.execute(
                delete(Department).where(Department.id == department_id)
            )
        if organization_id is not None:
            setup_db.execute(
                delete(Organization).where(Organization.id == organization_id)
            )
        setup_db.commit()
        setup_db.close()


if __name__ == "__main__":
    main()
