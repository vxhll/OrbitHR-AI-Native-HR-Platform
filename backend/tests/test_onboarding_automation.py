
from datetime import date, timedelta
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.db.database import get_db
from app.security.dependencies import get_current_user, require_hr


client = TestClient(app)
URL = "/api/onboarding/automation/overdue-tasks"


def make_hr():
    class FakeHR:
        email = "hr@orbithr.test"
        role = "HR"
        is_active = True

    return FakeHR()


def setup_overrides(db):
    def get_test_db():
        yield db

    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[require_hr] = lambda: None


def clear_overrides():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_hr, None)
    app.dependency_overrides.pop(get_current_user, None)


def test_overdue_tasks_requires_authentication():
    clear_overrides()

    response = client.get(URL)

    assert response.status_code == 401


def test_employee_cannot_access_overdue_report():
    class FakeEmployee:
        email = "employee@orbithr.test"
        role = "EMPLOYEE"
        is_active = True

    clear_overrides()
    app.dependency_overrides[get_current_user] = lambda: FakeEmployee()

    try:
        response = client.get(URL)
        assert response.status_code == 403
    finally:
        clear_overrides()


def test_hr_receives_overdue_tasks_report():
    clear_overrides()

    today = date.today()

    overdue_task = MagicMock()
    overdue_task.id = 11
    overdue_task.onboarding_case_id = 5
    overdue_task.task_code = "HR-001"
    overdue_task.title = "Complete employee profile"
    overdue_task.status = "Pending"
    overdue_task.due_date = today - timedelta(days=4)
    overdue_task.required = True

    onboarding_case = MagicMock()
    onboarding_case.id = 5
    onboarding_case.employee_id = 101
    onboarding_case.status = "In Progress"

    db = MagicMock()
    db.execute.return_value.all.return_value = [
        (overdue_task, onboarding_case)
    ]

    setup_overrides(db)

    try:
        response = client.get(URL)

        assert response.status_code == 200
        payload = response.json()

        assert payload["total_overdue_tasks"] == 1
        assert len(payload["tasks"]) == 1
        assert payload["tasks"][0]["task_id"] == 11
        assert payload["tasks"][0]["employee_id"] == 101
        assert payload["tasks"][0]["days_overdue"] == 4
        assert payload["tasks"][0]["status"] == "Pending"

        db.commit.assert_not_called()
        db.add.assert_not_called()
    finally:
        clear_overrides()


def test_hr_receives_empty_report_when_no_tasks_are_overdue():
    clear_overrides()

    db = MagicMock()
    db.execute.return_value.all.return_value = []
    setup_overrides(db)

    try:
        response = client.get(URL)

        assert response.status_code == 200
        payload = response.json()

        assert payload["total_overdue_tasks"] == 0
        assert payload["tasks"] == []

        db.commit.assert_not_called()
        db.add.assert_not_called()
    finally:
        clear_overrides()
