
from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.security.dependencies import get_current_user, require_hr


client = TestClient(app)

OFFBOARDING_URL = "/api/offboarding"


def test_offboarding_requires_authentication():
    response = client.post(
        OFFBOARDING_URL,
        json={
            "employee_id": "TEST-EMP-001",
            "exit_date": "2026-01-01",
            "exit_type": "RESIGNATION",
            "exit_reason": "Authorization test",
        },
    )

    assert response.status_code == 401


def test_employee_cannot_create_offboarding():
    class FakeUser:
        email = "employee@orbithr.test"
        role = "EMPLOYEE"
        is_active = True

    app.dependency_overrides[get_current_user] = lambda: FakeUser()

    try:
        response = client.post(
            OFFBOARDING_URL,
            json={
                "employee_id": "TEST-EMP-001",
                "exit_date": "2026-01-01",
                "exit_type": "RESIGNATION",
                "exit_reason": "Authorization test",
            },
        )

        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_offboarding_rejects_blank_employee_id():
    app.dependency_overrides[require_hr] = lambda: None

    try:
        response = client.post(
            OFFBOARDING_URL,
            json={
                "employee_id": "   ",
                "exit_date": date.today().isoformat(),
                "exit_type": "RESIGNATION",
                "exit_reason": "Validation test",
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(require_hr, None)


def test_offboarding_rejects_negative_notice_period():
    app.dependency_overrides[require_hr] = lambda: None

    try:
        response = client.post(
            OFFBOARDING_URL,
            json={
                "employee_id": "TEST-EMP-001",
                "exit_date": date.today().isoformat(),
                "exit_type": "RESIGNATION",
                "exit_reason": "Validation test",
                "notice_period_days": -1,
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(require_hr, None)


from unittest.mock import MagicMock

from fastapi import HTTPException

from app.db.database import get_db


def make_mock_db(employee=None, existing_exit=None):
    db = MagicMock()
    db.scalar.side_effect = [employee, existing_exit]
    return db


def override_db(db):
    def get_test_db():
        yield db

    app.dependency_overrides[get_db] = get_test_db


def hr_user():
    class FakeHR:
        email = "hr@orbithr.test"
        role = "HR"
        is_active = True

    return FakeHR()


def valid_payload():
    return {
        "employee_id": "TEST-EMP-001",
        "exit_date": "2026-01-01",
        "exit_type": "RESIGNATION",
        "exit_reason": "Test exit",
        "notice_period_days": 30,
        "rehire_eligible": False,
    }


def test_offboarding_rejects_future_exit_date():
    from datetime import date, timedelta

    from app.api.routes.offboarding import (
        OffboardingCreate,
        create_offboarding,
    )

    request = OffboardingCreate(
        **{
            **valid_payload(),
            "exit_date": (date.today() + timedelta(days=1)).isoformat(),
        }
    )

    db = MagicMock()

    try:
        try:
            create_offboarding(request=request, db=db)
            assert False, "Expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 400
            assert exc.detail == "Exit date cannot be in the future"

        db.scalar.assert_not_called()
        db.add.assert_not_called()
        db.commit.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_offboarding_rejects_missing_employee():
    from app.api.routes.offboarding import (
        OffboardingCreate,
        create_offboarding,
    )

    request = OffboardingCreate(**valid_payload())
    db = make_mock_db(employee=None)

    try:
        try:
            create_offboarding(request=request, db=db)
            assert False, "Expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 404
            assert exc.detail == "Employee not found"

        db.add.assert_not_called()
        db.commit.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_offboarding_rejects_duplicate_exit():
    from app.api.routes.offboarding import (
        OffboardingCreate,
        create_offboarding,
    )

    fake_employee = MagicMock()
    fake_existing_exit = MagicMock()
    request = OffboardingCreate(**valid_payload())
    db = make_mock_db(
        employee=fake_employee,
        existing_exit=fake_existing_exit,
    )

    try:
        try:
            create_offboarding(request=request, db=db)
            assert False, "Expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 409
            assert "already exists" in exc.detail

        db.add.assert_not_called()
        db.commit.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_offboarding_creates_exit_using_mocked_database():
    from app.api.routes.offboarding import (
        OffboardingCreate,
        create_offboarding,
    )
    from app.models.employee_exit import EmployeeExit

    fake_employee = MagicMock()
    request = OffboardingCreate(**valid_payload())
    db = make_mock_db(employee=fake_employee, existing_exit=None)

    def mock_refresh(record):
        record.id = 123

    db.refresh.side_effect = mock_refresh

    try:
        result = create_offboarding(request=request, db=db)

        assert isinstance(result, EmployeeExit)
        assert result.id == 123
        assert result.employee_id == "TEST-EMP-001"
        assert result.exit_date == request.exit_date
        assert result.exit_type == "RESIGNATION"
        assert result.exit_reason == "Test exit"
        assert result.notice_period_days == 30
        assert result.rehire_eligible is False
        assert result.status == "EXITED"

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(result)
    finally:
        app.dependency_overrides.pop(get_db, None)
