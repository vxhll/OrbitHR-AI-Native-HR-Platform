
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db.database import get_db
from app.main import app
from app.security.dependencies import require_hr


client = TestClient(app)
URL = "/api/analytics/attrition-features/EMP9999"


def test_missing_employee_returns_404():
    previous_overrides = app.dependency_overrides.copy()

    db = MagicMock()
    db.scalar.return_value = None

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_hr] = lambda: None

    try:
        response = client.get(URL)

        assert response.status_code == 404
        assert response.json()["detail"] == "Employee EMP9999 not found"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
