
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.db.database import get_db
from app.security.dependencies import get_current_user, require_hr


client = TestClient(app)
URL = "/api/onboarding/automation/reminders/run"


class FakeHR:
    email = "hr@orbithr.test"
    role = "HR"
    is_active = True


class FakeEmployee:
    email = "employee@orbithr.test"
    role = "EMPLOYEE"
    is_active = True


def setup_overrides(db=None, user=None):
    def get_test_db():
        yield db if db is not None else MagicMock()

    app.dependency_overrides[get_db] = get_test_db

    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user

    # Match the existing authorization convention used in the
    # onboarding endpoint tests.
    app.dependency_overrides[require_hr] = lambda: None


def clear_overrides():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_hr, None)
    app.dependency_overrides.pop(get_current_user, None)


def test_reminder_endpoint_requires_authentication():
    clear_overrides()

    try:
        response = client.post(URL, params={"dry_run": "true"})
        assert response.status_code == 401
    finally:
        clear_overrides()


def test_employee_cannot_trigger_reminders():
    clear_overrides()
    app.dependency_overrides[get_current_user] = (
        lambda: FakeEmployee()
    )

    try:
        response = client.post(URL, params={"dry_run": "true"})
        assert response.status_code == 403
    finally:
        clear_overrides()


def test_hr_can_preview_reminders_without_sending():
    clear_overrides()

    db = MagicMock()
    setup_overrides(db=db, user=FakeHR())

    preview_result = {
        "generated_on": "2026-10-23",
        "dry_run": True,
        "delivery_enabled": False,
        "eligible_tasks": 0,
        "results_count": 0,
        "results": [],
    }

    try:
        with patch(
            "app.api.routes.onboarding.run_onboarding_reminders",
            return_value=preview_result,
        ) as run_reminders:
            response = client.post(
                URL,
                params={"dry_run": "true"},
            )

        assert response.status_code == 200
        assert response.json()["dry_run"] is True
        assert response.json()["eligible_tasks"] == 0

        run_reminders.assert_called_once_with(
            db=db,
            dry_run=True,
        )
        db.commit.assert_not_called()
        db.add.assert_not_called()
    finally:
        clear_overrides()
