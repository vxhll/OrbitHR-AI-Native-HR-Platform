from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, UTC, timedelta
from threading import Barrier
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.engine import make_url

from app.db.database import SessionLocal, DATABASE_URL
from app.models.organization import Organization
from app.models.department import Department
from app.models.employee import Employee
from app.models.onboarding.case import OnboardingCase
from app.models.onboarding.task import OnboardingTask
from app.models.onboarding.reminder import OnboardingReminder
from app.services.onboarding_reminder_service import (
    REMINDER_STALE_CLAIM_TIMEOUT,
    _claim_reminder,
    _record_outcome,
)


def utcnow_naive():
    return datetime.now(UTC).replace(tzinfo=None)


def main():
    target = make_url(DATABASE_URL)
    if target.database != "orbithr_test_db":
        raise RuntimeError(
            f"Safety stop: expected orbithr_test_db, got {target.database!r}"
        )

    suffix = uuid4().hex[:12]
    employee_code = f"SR{suffix}"

    organization_id = department_id = case_id = task_id = None

    setup_db = SessionLocal()

    try:
        organization = Organization(name=f"Stale Recovery Test {suffix}")
        setup_db.add(organization)
        setup_db.flush()

        department = Department(
            name=f"Stale Recovery {suffix}",
            organization_id=organization.id,
        )
        setup_db.add(department)
        setup_db.flush()

        employee = Employee(
            employee_id=employee_code,
            full_name="Stale Recovery Concurrency Test",
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
            task_code=f"STALE_{suffix}",
            title="Stale recovery concurrency test task",
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
        old_token = str(uuid4())
        stale_time = now - REMINDER_STALE_CLAIM_TIMEOUT - timedelta(seconds=5)

        reminder = OnboardingReminder(
            task_id=task_id,
            recipient_email="stale-test@example.invalid",
            reminder_type="OVERDUE_DAILY",
            reminder_date=reminder_date,
            status="Sending",
            attempts=1,
            claim_token=old_token,
            claimed_at=stale_time,
            last_attempt_at=stale_time,
            created_at=now,
            error_message="Simulated expired claim",
        )
        setup_db.add(reminder)
        setup_db.commit()

        candidate = {
            "task_id": task_id,
            "recipient_email": "stale-test@example.invalid",
            "reminder_type": "OVERDUE_DAILY",
        }

        start_barrier = Barrier(2)

        def attempt_recovery():
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
                executor.submit(attempt_recovery),
                executor.submit(attempt_recovery),
            ]
            results = [future.result(timeout=30) for future in futures]

        winners = [result for result in results if isinstance(result, tuple)]
        non_winners = [result for result in results if isinstance(result, dict)]

        print("Database:", target.database)
        print("Stale recovery results:", results)
        print("Successful recovery claims:", len(winners))
        print("Non-winning outcomes:", non_winners)

        if len(winners) != 1:
            raise AssertionError(
                f"Expected exactly one recovery winner, got {len(winners)}"
            )

        recovered_id, new_token = winners[0]

        if recovered_id is None or not new_token:
            raise AssertionError("Winning recovery did not return a valid claim")

        if new_token == old_token:
            raise AssertionError("Recovery reused the expired claim token")

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
            print("New token differs from old token:", saved.claim_token != old_token)

            if saved.status != "Sending":
                raise AssertionError(
                    f"Expected Sending, got {saved.status!r}"
                )

            if saved.attempts != 2:
                raise AssertionError(
                    f"Expected attempts=2, got {saved.attempts}"
                )

            if saved.claim_token != new_token:
                raise AssertionError("Persisted claim token does not match winner")

            if saved.claimed_at is None:
                raise AssertionError("Expected claimed_at to be populated")

        # The expired worker must not be able to overwrite the new claim.
        with SessionLocal() as old_worker_db:
            old_worker_updated = _record_outcome(
                old_worker_db,
                reminder_id=recovered_id,
                claim_token=old_token,
                delivered=True,
            )

        print("Old claim token accepted:", old_worker_updated)

        if old_worker_updated is not False:
            raise AssertionError(
                "Expired claim unexpectedly updated the recovered reminder"
            )

        with SessionLocal() as verify_db:
            saved_after_old_worker = verify_db.execute(
                select(OnboardingReminder).where(
                    OnboardingReminder.task_id == task_id,
                    OnboardingReminder.reminder_type == "OVERDUE_DAILY",
                    OnboardingReminder.reminder_date == reminder_date,
                )
            ).scalar_one()

            if saved_after_old_worker.status != "Sending":
                raise AssertionError(
                    "Old claim changed the recovered reminder status"
                )

            if saved_after_old_worker.claim_token != new_token:
                raise AssertionError(
                    "Old claim changed the new worker's token"
                )

            if saved_after_old_worker.delivered_at is not None:
                raise AssertionError(
                    "Old claim unexpectedly marked the reminder delivered"
                )

        print(
            "PASS: one worker recovered the stale claim; "
            "the expired token could not overwrite it"
        )

    finally:
        setup_db.rollback()

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

        setup_db.execute(
            delete(Employee).where(
                Employee.employee_id == employee_code
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
