import os
import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.auth.user import User
from app.models.employee import Employee
from app.models.onboarding import (
    OnboardingCase,
    OnboardingReminder,
    OnboardingTask,
)


MAX_REMINDER_ATTEMPTS = 3
REMINDER_RETRY_DELAY = timedelta(minutes=15)
REMINDER_STALE_CLAIM_TIMEOUT = timedelta(minutes=15)


def _utcnow() -> datetime:
    """Return naive UTC for existing database DateTime columns."""
    return datetime.now(UTC).replace(tzinfo=None)


def _get_active_overdue_tasks(
    db: Session,
    today: date,
) -> list[dict[str, Any]]:
    """Return overdue onboarding tasks and their active recipients."""
    result = db.execute(
        select(OnboardingTask, OnboardingCase, User)
        .join(
            OnboardingCase,
            OnboardingTask.onboarding_case_id == OnboardingCase.id,
        )
        .join(
            Employee,
            Employee.employee_id == OnboardingCase.employee_id,
        )
        .join(
            User,
            User.employee_id == Employee.employee_id,
        )
        .where(
            OnboardingTask.due_date.is_not(None),
            OnboardingTask.due_date < today,
            OnboardingTask.status != "Completed",
            OnboardingCase.status != "Completed",
            User.is_active.is_(True),
        )
        .order_by(
            OnboardingTask.due_date.asc(),
            OnboardingTask.id.asc(),
        )
    )

    return [
        {
            "task_id": task.id,
            "onboarding_case_id": case.id,
            "employee_id": case.employee_id,
            "task_code": task.task_code,
            "title": task.title,
            "status": task.status,
            "due_date": task.due_date,
            "days_overdue": (today - task.due_date).days,
            "recipient_email": user.email,
            "reminder_type": "OVERDUE_DAILY",
        }
        for task, case, user in result.all()
    ]


def _send_reminder(
    webhook_url: str,
    reminder: dict[str, Any],
) -> None:
    """Send a reminder to the configured Power Automate webhook."""
    payload = {
        "event": "onboarding_task_overdue",
        "task_id": reminder["task_id"],
        "onboarding_case_id": reminder["onboarding_case_id"],
        "employee_id": reminder["employee_id"],
        "task_code": reminder["task_code"],
        "title": reminder["title"],
        "due_date": reminder["due_date"].isoformat(),
        "days_overdue": reminder["days_overdue"],
        "recipient_email": reminder["recipient_email"],
        "reminder_type": reminder["reminder_type"],
    }

    response = httpx.post(
        webhook_url,
        json=payload,
        timeout=10.0,
    )
    response.raise_for_status()


def _safe_error_message(exc: Exception) -> str:
    """Avoid storing webhook URLs or request details."""
    return f"{type(exc).__name__}: reminder delivery failed"


def _existing_result(
    existing: OnboardingReminder,
    now: datetime,
) -> dict[str, Any]:
    """Determine whether an existing reminder can be claimed or recovered."""
    if existing.status == "Delivered":
        return {"result": "already_delivered"}

    if existing.status == "Sending":
        if existing.claimed_at is None or existing.claim_token is None:
            return {"result": "manual_review"}

        elapsed = now - existing.claimed_at

        if elapsed < REMINDER_STALE_CLAIM_TIMEOUT:
            return {
                "result": "sending",
                "retry_after_seconds": max(
                    1,
                    int(
                        (
                            REMINDER_STALE_CLAIM_TIMEOUT - elapsed
                        ).total_seconds()
                    ),
                ),
            }

        if existing.attempts >= MAX_REMINDER_ATTEMPTS:
            return {"result": "manual_review"}

        return {"result": "claim_stale"}

    if existing.status != "Failed":
        return {"result": "already_recorded"}

    if existing.attempts >= MAX_REMINDER_ATTEMPTS:
        return {"result": "retry_limit_reached"}

    if existing.last_attempt_at is None:
        return {"result": "retry_not_scheduled"}

    elapsed = now - existing.last_attempt_at

    if elapsed < REMINDER_RETRY_DELAY:
        return {
            "result": "retry_wait",
            "retry_after_seconds": max(
                1,
                int((REMINDER_RETRY_DELAY - elapsed).total_seconds()),
            ),
        }

    return {"result": "claim_retry"}


def _claim_reminder(
    db: Session,
    candidate: dict[str, Any],
    reminder_date: datetime,
    now: datetime,
) -> tuple[int, str] | dict[str, Any]:
    """
    Atomically claim, retry, or recover one reminder.

    The claim is committed before the webhook is called. Conditional
    updates and the claim token ensure that only one worker owns a
    reminder at a time.

    Recovering a stale claim increments the attempt count because the
    previous delivery outcome may be uncertain.
    """
    task_id = candidate["task_id"]
    reminder_type = candidate["reminder_type"]
    token = str(uuid.uuid4())

    existing = db.execute(
        select(OnboardingReminder).where(
            OnboardingReminder.task_id == task_id,
            OnboardingReminder.reminder_type == reminder_type,
            OnboardingReminder.reminder_date == reminder_date,
        )
    ).scalar_one_or_none()

    if existing is None:
        statement = (
            pg_insert(OnboardingReminder)
            .values(
                task_id=task_id,
                recipient_email=candidate["recipient_email"],
                reminder_type=reminder_type,
                reminder_date=reminder_date,
                status="Sending",
                attempts=1,
                last_attempt_at=now,
                claim_token=token,
                claimed_at=now,
                created_at=now,
                error_message=None,
            )
            .on_conflict_do_nothing(
                constraint="uq_onboarding_reminder_task_type_date"
            )
            .returning(OnboardingReminder.id)
        )

        reminder_id = db.execute(statement).scalar_one_or_none()

        if reminder_id is not None:
            db.commit()
            return reminder_id, token

        # Another worker inserted the unique reminder first.
        db.rollback()

        existing = db.execute(
            select(OnboardingReminder).where(
                OnboardingReminder.task_id == task_id,
                OnboardingReminder.reminder_type == reminder_type,
                OnboardingReminder.reminder_date == reminder_date,
            )
        ).scalar_one_or_none()

        if existing is None:
            return {"result": "claim_conflict"}

    decision = _existing_result(existing, now)
    decision_type = decision["result"]
    claim_stale = decision_type == "claim_stale"

    if decision_type not in {"claim_retry", "claim_stale"}:
        return decision

    if claim_stale:
        # Only the worker that observed this exact stale claim token
        # can replace it. Incomplete legacy claims require manual review.
        statement = (
            update(OnboardingReminder)
            .where(
                OnboardingReminder.id == existing.id,
                OnboardingReminder.status == "Sending",
                OnboardingReminder.claim_token.is_not(None),
                OnboardingReminder.claim_token == existing.claim_token,
                OnboardingReminder.claimed_at.is_not(None),
                OnboardingReminder.claimed_at
                <= now - REMINDER_STALE_CLAIM_TIMEOUT,
                OnboardingReminder.attempts < MAX_REMINDER_ATTEMPTS,
            )
            .values(
                status="Sending",
                attempts=OnboardingReminder.attempts + 1,
                last_attempt_at=now,
                claim_token=token,
                claimed_at=now,
                error_message=(
                    "Previous claim expired; delivery outcome uncertain"
                ),
            )
            .returning(OnboardingReminder.id)
        )
    else:
        # Only one worker can change an eligible Failed reminder to Sending.
        statement = (
            update(OnboardingReminder)
            .where(
                OnboardingReminder.id == existing.id,
                OnboardingReminder.status == "Failed",
                OnboardingReminder.attempts < MAX_REMINDER_ATTEMPTS,
                OnboardingReminder.last_attempt_at.is_not(None),
                OnboardingReminder.last_attempt_at
                <= now - REMINDER_RETRY_DELAY,
            )
            .values(
                status="Sending",
                attempts=OnboardingReminder.attempts + 1,
                last_attempt_at=now,
                claim_token=token,
                claimed_at=now,
                error_message=None,
            )
            .returning(OnboardingReminder.id)
        )

    reminder_id = db.execute(statement).scalar_one_or_none()

    if reminder_id is not None:
        db.commit()
        return reminder_id, token

    # Another worker may have changed the row after our initial read.
    db.rollback()

    latest = db.execute(
        select(OnboardingReminder).where(
            OnboardingReminder.task_id == task_id,
            OnboardingReminder.reminder_type == reminder_type,
            OnboardingReminder.reminder_date == reminder_date,
        )
    ).scalar_one_or_none()

    if latest is None:
        return {"result": "claim_conflict"}

    latest_decision = _existing_result(latest, _utcnow())

    if latest_decision["result"] in {"claim_retry", "claim_stale"}:
        return {"result": "claim_conflict"}

    return latest_decision


def _record_outcome(
    db: Session,
    reminder_id: int,
    claim_token: str,
    *,
    delivered: bool,
    error_message: str | None = None,
) -> bool:
    """Persist an outcome only if this worker still owns the claim."""
    now = _utcnow()

    values: dict[str, Any] = {
        "status": "Delivered" if delivered else "Failed",
        "delivered_at": now if delivered else None,
        "error_message": error_message,
        "claim_token": None,
        "claimed_at": None,
    }

    try:
        result = db.execute(
            update(OnboardingReminder)
            .where(
                OnboardingReminder.id == reminder_id,
                OnboardingReminder.claim_token == claim_token,
                OnboardingReminder.status == "Sending",
            )
            .values(**values)
        )

        if result.rowcount != 1:
            db.rollback()
            return False

        db.commit()
        return True

    except Exception:
        db.rollback()
        raise


def run_onboarding_reminders(
    db: Session,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """
    Preview or dispatch overdue onboarding reminders.

    Claims are committed before HTTP requests. Delivery outcomes are
    recorded separately. Stale Sending claims may be recovered after
    the timeout when attempts remain; uncertain outcomes consume an attempt.

    Failed attempts are limited to three per task, reminder type, and date,
    with at least 15 minutes between failed attempts.

    Dry runs do not query reminder history or modify the database.
    """
    today = date.today()
    reminder_date = datetime.combine(today, time.min)
    candidates = _get_active_overdue_tasks(db, today)

    webhook_url = os.getenv(
        "POWER_AUTOMATE_ONBOARDING_WEBHOOK_URL",
        "",
    ).strip()

    delivery_enabled = (
        os.getenv("ONBOARDING_REMINDERS_ENABLED", "false").lower()
        == "true"
        and bool(webhook_url)
    )

    results: list[dict[str, Any]] = []

    if dry_run:
        results = [
            {**candidate, "result": "dry_run"}
            for candidate in candidates
        ]

    elif not delivery_enabled:
        results = [
            {**candidate, "result": "delivery_disabled"}
            for candidate in candidates
        ]

    else:
        # End the read-only candidate-query transaction before claims.
        db.rollback()

        for candidate in candidates:
            try:
                claim = _claim_reminder(
                    db,
                    candidate,
                    reminder_date,
                    _utcnow(),
                )
            except Exception:
                db.rollback()
                raise

            if isinstance(claim, dict):
                results.append({**candidate, **claim})
                continue

            reminder_id, claim_token = claim

            try:
                _send_reminder(webhook_url, candidate)

            except Exception as exc:
                try:
                    saved = _record_outcome(
                        db,
                        reminder_id,
                        claim_token,
                        delivered=False,
                        error_message=_safe_error_message(exc),
                    )
                except Exception:
                    # If the outcome transaction fails, the persisted row
                    # may remain Sending and require manual review.
                    raise

                results.append({
                    **candidate,
                    "result": "failed" if saved else "manual_review",
                    "error": type(exc).__name__,
                    "attempts": _get_attempt_count(db, reminder_id),
                })
                continue

            try:
                saved = _record_outcome(
                    db,
                    reminder_id,
                    claim_token,
                    delivered=True,
                )
            except Exception:
                # The webhook may have succeeded. Do not automatically retry.
                raise

            results.append({
                **candidate,
                "result": "delivered" if saved else "manual_review",
                "attempts": _get_attempt_count(db, reminder_id),
            })

    return {
        "generated_on": today.isoformat(),
        "dry_run": dry_run,
        "delivery_enabled": delivery_enabled,
        "eligible_tasks": len(candidates),
        "results_count": len(results),
        "results": results,
    }


def _get_attempt_count(
    db: Session,
    reminder_id: int,
) -> int | None:
    """Read the attempt count without retaining a transaction."""
    try:
        attempts = db.execute(
            select(OnboardingReminder.attempts).where(
                OnboardingReminder.id == reminder_id
            )
        ).scalar_one_or_none()

        db.rollback()
        return attempts

    except Exception:
        db.rollback()
        return None
