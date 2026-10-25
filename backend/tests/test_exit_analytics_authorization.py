
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db.database import get_db
from app.main import app
from app.models.auth.user import User
from app.security.dependencies import get_current_user, require_hr
from app.security.security import create_access_token


client = TestClient(app)
URL = "/api/analytics/exits"


def make_user(user_id: int, role: str, is_active: bool = True):
    """Create a mocked database user for authorization tests."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.role = role
    user.is_active = is_active
    return user


def setup_user(user=None):
    """Keep the real require_hr and get_current_user dependencies active."""
    app.dependency_overrides.pop(require_hr, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)

    if user is not None:
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = user

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db


def teardown_overrides():
    app.dependency_overrides.pop(require_hr, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


def make_token(user_id: int, role: str) -> str:
    return create_access_token(
        user_id=user_id,
        employee_id=f"TEST-{role}-{user_id}",
        role=role,
    )


def mock_analytics_database():
    """Return an empty analytics database response."""
    db = MagicMock()
    db.scalar.side_effect = [0, 0, None, 0, 0]

    result = MagicMock()
    result.all.return_value = []
    db.execute.return_value = result

    return db


def test_exit_analytics_requires_authentication():
    setup_user()

    try:
        response = client.get(URL)
        assert response.status_code == 401
    finally:
        teardown_overrides()


def test_employee_cannot_access_exit_analytics():
    user = make_user(1, "EMPLOYEE")
    setup_user(user)

    try:
        response = client.get(
            URL,
            headers={"Authorization": f"Bearer {make_token(1, 'EMPLOYEE')}"},
        )
        assert response.status_code == 403
    finally:
        teardown_overrides()


def test_manager_cannot_access_exit_analytics():
    user = make_user(2, "MANAGER")
    setup_user(user)

    try:
        response = client.get(
            URL,
            headers={"Authorization": f"Bearer {make_token(2, 'MANAGER')}"},
        )
        assert response.status_code == 403
    finally:
        teardown_overrides()


def test_recruiter_cannot_access_exit_analytics():
    user = make_user(3, "RECRUITER")
    setup_user(user)

    try:
        response = client.get(
            URL,
            headers={"Authorization": f"Bearer {make_token(3, 'RECRUITER')}"},
        )
        assert response.status_code == 403
    finally:
        teardown_overrides()


def test_inactive_hr_cannot_access_exit_analytics():
    user = make_user(4, "HR", is_active=False)
    setup_user(user)

    try:
        response = client.get(
            URL,
            headers={"Authorization": f"Bearer {make_token(4, 'HR')}"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "User account is inactive"
    finally:
        teardown_overrides()


def test_active_hr_can_access_exit_analytics():
    user = make_user(5, "HR")
    setup_user(user)

    try:
        # Use a separate database mock for the analytics queries.
        analytics_db = mock_analytics_database()

        def override_db():
            yield analytics_db

        app.dependency_overrides[get_db] = override_db

        # The current-user dependency also uses get_db, so its user
        # lookup must be provided by the same mock.
        analytics_db.query.return_value.filter.return_value.first.return_value = user

        response = client.get(
            URL,
            headers={"Authorization": f"Bearer {make_token(5, 'HR')}"},
        )

        assert response.status_code == 200
        assert response.json()["total_recorded_exits"] == 0
    finally:
        teardown_overrides()


def test_active_admin_can_access_exit_analytics():
    user = make_user(6, "ADMIN")
    setup_user(user)

    try:
        analytics_db = mock_analytics_database()

        def override_db():
            yield analytics_db

        app.dependency_overrides[get_db] = override_db
        analytics_db.query.return_value.filter.return_value.first.return_value = user

        response = client.get(
            URL,
            headers={"Authorization": f"Bearer {make_token(6, 'ADMIN')}"},
        )

        assert response.status_code == 200
        assert response.json()["total_recorded_exits"] == 0
    finally:
        teardown_overrides()
