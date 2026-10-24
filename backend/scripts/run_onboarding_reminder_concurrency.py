
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, UTC
from threading import Barrier
from uuid import uuid4

from sqlalchemy import delete

from app.db.database import SessionLocal
from app.models.organization import Organization
from app.models.department import Department
from app.models.employee import Employee
from app.models.onboarding.case import OnboardingCase
from app.models.onboarding.task import OnboardingTask
from app.models.onboarding.reminder import OnboardingReminder
from app.services.onboarding_reminder_service import _claim_reminder


def utcnow_naive():
    return datetime.now(UTC).replace(tzinfo=None)


def main():
    # Refuse to run against the main database.
    from app.db.database import DATABASE_URL
    from sqlalchemy.engine import make_url

    target = make_url(DATABASE_URL)

    if target.database != "orbithr_test_db":
        raise RuntimeError(
            "Safety stop: DATABASE_URL must target orbithr_test_db. "
            f"Current target: {target.database!r}"
        )

    suffix = uuid4().hex[:12]
    employee_code = f"CT{suffix}"
    organization_name = f"Concurrency Test {suffix}"

    organization_id = None
    department_id = None
    case_id = None
    task_id = None
    employee_id = employee_code

    setup_db = SessionLocal()

    try:
        organization = Organization(name=organization_name)
        setup_db.add(organization)
        setup_db.flush()

        department = Department(
            name=f"Concurrency {suffix}",
            organization_id=organization.id,
        )
        setup_db.add(department)
        setup_db.flush()

        employee = Employee(
            employee_id=employee_code,
            full_name="Concurrency Test Employee",
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
            task_code=f"TEST_{suffix}",
            title="Concurrency test task",
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

        setup_db.commit()

        candidate = {
            "task_id": task_id,
            "recipient_email": "concurrency-test@example.invalid",
            "reminder_type": "OVERDUE_DAILY",
        }
        reminder_date = datetime.combine(date.today(), time.min)

        # Both workers start their claim attempt together.
        start_barrier = Barrier(2)

        def attempt_claim():
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
                executor.submit(attempt_claim),
                executor.submit(attempt_claim),
            ]
            results = [future.result(timeout=30) for future in futures]

        winners = [
            result for result in results
            if isinstance(result, tuple)
        ]
        non_winners = [
            result for result in results
            if isinstance(result, dict)
        ]

        print("Database:", target.database)
        print("Claim results:", results)
        print("Successful claims:", len(winners))
        print("Non-winning outcomes:", non_winners)

        if len(winners) != 1:
            raise AssertionError(
                f"Expected exactly one claim winner, got {len(winners)}"
            )

        # A competing worker should recognize the in-progress claim.
        if not non_winners:
            raise AssertionError(
                "Expected the other worker to return a non-winning outcome"
            )

        with SessionLocal() as verify_db:
            reminders = verify_db.execute(
                __import__("sqlalchemy").select(OnboardingReminder).where(
                    OnboardingReminder.task_id == task_id,
                    OnboardingReminder.reminder_type == "OVERDUE_DAILY",
                    OnboardingReminder.reminder_date == reminder_date,
                )
            ).scalars().all()

            if len(reminders) != 1:
                raise AssertionError(
                    f"Expected one reminder row, found {len(reminders)}"
                )

            reminder = reminders[0]
            if reminder.status != "Sending":
                raise AssertionError(
                    f"Expected Sending status, got {reminder.status!r}"
                )
            if not reminder.claim_token:
                raise AssertionError("Expected a persisted claim token")

        print("Reminder rows for test task: 1")
        print("Persisted status: Sending")
        print("Persisted claim token: present")
        print("PASS: only one worker acquired the reminder claim")

    finally:
        setup_db.rollback()

        # Delete only records created by this run, in FK-safe order.
        if task_id is not None:
            setup_db.execute(
                delete(OnboardingReminder).where(
                    OnboardingReminder.task_id == task_id
                )
            )
            setup_db.execute(
                delete(OnboardingTask).where(
                    OnboardingTask.id == task_id
                )
            )

        if case_id is not None:
            setup_db.execute(
                delete(OnboardingCase).where(
                    OnboardingCase.id == case_id
                )
            )

        if employee_id is not None:
            setup_db.execute(
                delete(Employee).where(
                    Employee.employee_id == employee_id
                )
            )

        if department_id is not None:
            setup_db.execute(
                delete(Department).where(
                    Department.id == department_id
                )
            )

        if organization_id is not None:
            setup_db.execute(
                delete(Organization).where(
                    Organization.id == organization_id
                )
            )

        setup_db.commit()
        setup_db.close()


if __name__ == "__main__":
    main()
