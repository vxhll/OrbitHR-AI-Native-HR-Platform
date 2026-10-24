from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, call, patch

import pytest

from app.services.onboarding_reminder_service import (
    MAX_REMINDER_ATTEMPTS,
    REMINDER_RETRY_DELAY,
    REMINDER_STALE_CLAIM_TIMEOUT,
    _existing_result,
    _record_outcome,
    run_onboarding_reminders,
)


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def overdue_candidate():
    candidate = MagicMock()
    candidate.task_id = 101
    candidate.task_title = "Complete employee documents"
    candidate.due_date = date.today() - timedelta(days=2)
    candidate.employee_id = 201
    candidate.employee_name = "Test Employee"
    candidate.employee_email = "employee@example.com"
    candidate.case_id = 301
    candidate.organization_id = 401
    return candidate


def make_existing_reminder(
    *,
    status="Failed",
    attempts=1,
    claim_token=None,
    claimed_at=None,
    last_attempt_at=None,
    delivered_at=None,
):
    reminder = MagicMock()
    reminder.id = 501
    reminder.status = status
    reminder.attempts = attempts
    reminder.claim_token = claim_token
    reminder.claimed_at = claimed_at
    reminder.last_attempt_at = last_attempt_at
    reminder.delivered_at = delivered_at
    reminder.error_message = None
    return reminder


# ---------------------------------------------------------------------------
# Existing reminder state and retry policy
# ---------------------------------------------------------------------------


def test_delivered_reminder_is_not_sent_again():
    now = datetime.now(UTC).replace(tzinfo=None)
    existing = make_existing_reminder(
        status="Delivered",
        attempts=1,
        delivered_at=now - timedelta(minutes=5),
    )

    result = _existing_result(existing, now)

    assert result["result"] == "already_delivered"


def test_recent_sending_claim_is_not_claimed_again():
    now = datetime.now(UTC).replace(tzinfo=None)
    claimed_at = now - timedelta(minutes=5)
    existing = make_existing_reminder(
        status="Sending",
        attempts=1,
        claim_token="active-token",
        claimed_at=claimed_at,
        last_attempt_at=claimed_at,
    )

    result = _existing_result(existing, now)

    assert result["result"] == "sending"
    assert result["retry_after_seconds"] > 0


def test_sending_reminder_without_claim_timestamp_requires_manual_review():
    now = datetime.now(UTC).replace(tzinfo=None)
    existing = make_existing_reminder(
        status="Sending",
        attempts=1,
        claim_token="active-token",
        claimed_at=None,
        last_attempt_at=now - timedelta(hours=1),
    )

    result = _existing_result(existing, now)

    assert result["result"] == "manual_review"


def test_sending_reminder_without_claim_token_requires_manual_review():
    now = datetime.now(UTC).replace(tzinfo=None)
    existing = make_existing_reminder(
        status="Sending",
        attempts=1,
        claim_token=None,
        claimed_at=now - timedelta(hours=1),
        last_attempt_at=now - timedelta(hours=1),
    )

    result = _existing_result(existing, now)

    assert result["result"] == "manual_review"


def test_stale_sending_reminder_is_eligible_for_recovery():
    now = datetime.now(UTC).replace(tzinfo=None)
    stale_time = now - REMINDER_STALE_CLAIM_TIMEOUT - timedelta(seconds=1)
    existing = make_existing_reminder(
        status="Sending",
        attempts=1,
        claim_token="old-token",
        claimed_at=stale_time,
        last_attempt_at=stale_time,
    )

    result = _existing_result(existing, now)

    assert result["result"] == "claim_stale"


def test_stale_sending_claim_at_attempt_limit_requires_manual_review():
    now = datetime.now(UTC).replace(tzinfo=None)
    stale_time = now - REMINDER_STALE_CLAIM_TIMEOUT - timedelta(seconds=1)
    existing = make_existing_reminder(
        status="Sending",
        attempts=MAX_REMINDER_ATTEMPTS,
        claim_token="old-token",
        claimed_at=stale_time,
        last_attempt_at=stale_time,
    )

    result = _existing_result(existing, now)

    assert result["result"] == "manual_review"


def test_failed_reminder_waits_for_retry_delay():
    now = datetime.now(UTC).replace(tzinfo=None)
    last_attempt_at = now - timedelta(minutes=5)
    existing = make_existing_reminder(
        status="Failed",
        attempts=1,
        last_attempt_at=last_attempt_at,
    )

    result = _existing_result(existing, now)

    assert result["result"] == "retry_wait"


def test_failed_reminder_can_retry_after_delay():
    now = datetime.now(UTC).replace(tzinfo=None)
    last_attempt_at = now - REMINDER_RETRY_DELAY - timedelta(seconds=1)
    existing = make_existing_reminder(
        status="Failed",
        attempts=1,
        last_attempt_at=last_attempt_at,
    )

    result = _existing_result(existing, now)

    assert result["result"] == "claim_retry"


def test_failed_reminder_at_attempt_limit_is_not_retried():
    now = datetime.now(UTC).replace(tzinfo=None)
    existing = make_existing_reminder(
        status="Failed",
        attempts=MAX_REMINDER_ATTEMPTS,
        last_attempt_at=now - timedelta(hours=1),
    )

    result = _existing_result(existing, now)

    assert result["result"] == "retry_limit_reached"


def test_failed_reminder_without_last_attempt_time_is_not_retried():
    now = datetime.now(UTC).replace(tzinfo=None)
    existing = make_existing_reminder(
        status="Failed",
        attempts=1,
        last_attempt_at=None,
    )

    result = _existing_result(existing, now)

    assert result["result"] == "retry_not_scheduled"


def test_unknown_existing_status_is_not_reclaimed():
    now = datetime.now(UTC).replace(tzinfo=None)
    existing = make_existing_reminder(
        status="Pending",
        attempts=0,
    )

    result = _existing_result(existing, now)

    assert result["result"] == "already_recorded"


# ---------------------------------------------------------------------------
# Conditional reminder outcome updates
# ---------------------------------------------------------------------------


def test_record_outcome_commits_successful_delivery_update():
    db = MagicMock()
    result = MagicMock()
    result.rowcount = 1
    db.execute.return_value = result

    delivered_at = datetime.now(UTC).replace(tzinfo=None)

    recorded = _record_outcome(
        db,
        reminder_id=501,
        claim_token="current-token",
        delivered=True,
    )

    assert recorded is True
    db.execute.assert_called_once()
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_record_outcome_commits_failed_delivery_update():
    db = MagicMock()
    result = MagicMock()
    result.rowcount = 1
    db.execute.return_value = result

    recorded = _record_outcome(
        db,
        reminder_id=501,
        claim_token="current-token",
        delivered=False,
        error_message="Delivery failed",
    )

    assert recorded is True
    db.execute.assert_called_once()
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_record_outcome_rolls_back_when_claim_no_longer_matches():
    db = MagicMock()
    result = MagicMock()
    result.rowcount = 0
    db.execute.return_value = result

    recorded = _record_outcome(
        db,
        reminder_id=501,
        claim_token="old-token",
        delivered=True,
    )

    assert recorded is False
    db.execute.assert_called_once()
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_record_outcome_rolls_back_and_reraises_database_error():
    db = MagicMock()
    db.execute.side_effect = RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        _record_outcome(
            db,
            reminder_id=501,
            claim_token="current-token",
            delivered=True,
        )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Reminder runner safety checks
# ---------------------------------------------------------------------------


def test_dry_run_does_not_send_reminders(db):
    with (
        patch(
            "app.services.onboarding_reminder_service._get_active_overdue_tasks",
            return_value=[],
        ) as get_tasks,
        patch(
            "app.services.onboarding_reminder_service._send_reminder"
        ) as send_reminder,
    ):
        result = run_onboarding_reminders(db, dry_run=True)

    get_tasks.assert_called_once()
    send_reminder.assert_not_called()
    assert isinstance(result, dict)


def test_disabled_delivery_does_not_send_reminders(db):
    with (
        patch.dict(
            "os.environ",
            {
                "ONBOARDING_REMINDERS_ENABLED": "false",
                "POWER_AUTOMATE_WEBHOOK_URL": "https://example.invalid/webhook",
            },
        ),
        patch(
            "app.services.onboarding_reminder_service._get_active_overdue_tasks",
            return_value=[],
        ),
        patch(
            "app.services.onboarding_reminder_service._send_reminder"
        ) as send_reminder,
    ):
        result = run_onboarding_reminders(db, dry_run=False)

    send_reminder.assert_not_called()
    assert isinstance(result, dict)


def test_missing_webhook_does_not_send_reminders(db):
    with (
        patch.dict(
            "os.environ",
            {
                "ONBOARDING_REMINDERS_ENABLED": "true",
                "POWER_AUTOMATE_WEBHOOK_URL": "",
            },
        ),
        patch(
            "app.services.onboarding_reminder_service._get_active_overdue_tasks",
            return_value=[],
        ),
        patch(
            "app.services.onboarding_reminder_service._send_reminder"
        ) as send_reminder,
    ):
        result = run_onboarding_reminders(db, dry_run=False)

    send_reminder.assert_not_called()
    assert isinstance(result, dict)


def test_outcome_database_error_is_not_silently_retried():
    db = MagicMock()
    db.execute.side_effect = RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        _record_outcome(
            db,
            reminder_id=501,
            claim_token="current-token",
            delivered=True,
        )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()
