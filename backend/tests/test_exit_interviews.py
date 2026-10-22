
from datetime import date
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db.database import get_db
from app.main import app
from app.security.dependencies import get_current_user, require_hr
from app.models.exit_interview import ExitInterview


client = TestClient(app)
URL = "/api/exit-interviews"


def cleanup_overrides():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_hr, None)


def mock_db(db):
    def get_test_db():
        yield db

    app.dependency_overrides[get_db] = get_test_db


def valid_payload():
    return {
        "employee_id": "TEST-EMP-001",
        "interview_date": date.today().isoformat(),
        "reason_for_leaving": "Career growth",
        "feedback_on_management": "Positive",
        "feedback_on_work_environment": "Good",
        "feedback_on_career_growth": "Limited opportunities",
        "overall_satisfaction_1to10": 7,
        "would_recommend_company": True,
        "additional_comments": "Test only",
    }


def test_exit_interview_requires_authentication():
    cleanup_overrides()

    response = client.post(URL, json=valid_payload())

    assert response.status_code == 401


def test_exit_interview_employee_role_is_forbidden():
    cleanup_overrides()

    class FakeUser:
        email = "employee@orbithr.test"
        role = "EMPLOYEE"
        is_active = True

    app.dependency_overrides[get_current_user] = lambda: FakeUser()

    try:
        response = client.post(URL, json=valid_payload())
        assert response.status_code == 403
    finally:
        cleanup_overrides()


def test_exit_interview_rejects_invalid_satisfaction_score():
    cleanup_overrides()
    app.dependency_overrides[require_hr] = lambda: None

    try:
        payload = valid_payload()
        payload["overall_satisfaction_1to10"] = 11

        response = client.post(URL, json=payload)

        assert response.status_code == 422
    finally:
        cleanup_overrides()


def test_exit_interview_rejects_missing_employee():
    cleanup_overrides()
    app.dependency_overrides[require_hr] = lambda: None

    db = MagicMock()
    db.scalar.return_value = None
    mock_db(db)

    try:
        response = client.post(URL, json=valid_payload())

        assert response.status_code == 404
        assert response.json()["detail"] == "Employee not found"
        db.add.assert_not_called()
        db.commit.assert_not_called()
    finally:
        cleanup_overrides()


def test_exit_interview_requires_operational_exit_record():
    cleanup_overrides()
    app.dependency_overrides[require_hr] = lambda: None

    db = MagicMock()
    db.scalar.side_effect = [MagicMock(), None]
    mock_db(db)

    try:
        response = client.post(URL, json=valid_payload())

        assert response.status_code == 409
        assert "operational exit record is required" in response.json()["detail"]
        db.add.assert_not_called()
        db.commit.assert_not_called()
    finally:
        cleanup_overrides()


def test_exit_interview_creates_record_using_mocked_database():
    cleanup_overrides()
    app.dependency_overrides[require_hr] = lambda: None

    db = MagicMock()
    db.scalar.side_effect = [MagicMock(), MagicMock()]

    def refresh_record(record):
        record.id = 456

    db.refresh.side_effect = refresh_record
    mock_db(db)

    try:
        response = client.post(URL, json=valid_payload())

        assert response.status_code == 201
        body = response.json()
        assert body["id"] == 456
        assert body["employee_id"] == "TEST-EMP-001"
        assert body["reason_for_leaving"] == "Career growth"
        assert body["overall_satisfaction_1to10"] == 7
        assert body["would_recommend_company"] is True

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()
    finally:
        cleanup_overrides()


def test_exit_interview_retrieval_returns_404_when_missing():
    cleanup_overrides()
    app.dependency_overrides[require_hr] = lambda: None

    db = MagicMock()
    db.get.return_value = None
    mock_db(db)

    try:
        response = client.get(f"{URL}/999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Exit interview not found"
    finally:
        cleanup_overrides()


def test_exit_interview_retrieval_returns_record():
    cleanup_overrides()
    app.dependency_overrides[require_hr] = lambda: None

    interview = ExitInterview(
        id=456,
        employee_id="TEST-EMP-001",
        interview_date=date.today(),
        reason_for_leaving="Career growth",
        feedback_on_management="Positive",
        feedback_on_work_environment="Good",
        feedback_on_career_growth="Limited opportunities",
        overall_satisfaction_1to10=7,
        would_recommend_company=True,
        additional_comments="Test only",
    )

    db = MagicMock()
    db.get.return_value = interview
    mock_db(db)

    try:
        response = client.get(f"{URL}/456")

        assert response.status_code == 200
        assert response.json()["id"] == 456
        assert response.json()["employee_id"] == "TEST-EMP-001"
        assert response.json()["overall_satisfaction_1to10"] == 7
    finally:
        cleanup_overrides()
