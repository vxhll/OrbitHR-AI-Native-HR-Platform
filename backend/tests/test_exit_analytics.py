from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from app.security.dependencies import require_hr
from app.db.database import get_db
from app.main import app


client = TestClient(app)
URL = "/api/analytics/exits"


def cleanup_overrides():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_hr, None)
    app.dependency_overrides[require_hr] = lambda: None

def mock_db(db):
    def get_test_db():
        yield db

    app.dependency_overrides[get_db] = get_test_db


def test_exit_analytics_returns_operational_exit_metrics():
    cleanup_overrides()

    db = MagicMock()

    # Scalar query results, in the order used by the endpoint.
    db.scalar.side_effect = [
        3,       # Total recorded exits
        2,       # Total interviews
        7.5,     # Average satisfaction
        2,       # Recommendation responses
        1,       # Yes responses
    ]

    # 1. Exit type breakdown
    exit_types_result = MagicMock()
    exit_types_result.all.return_value = [
        ("RESIGNATION", 2),
        ("TERMINATION", 1),
    ]

    # 2. Monthly exit trends
    monthly_result = MagicMock()
    monthly_result.all.return_value = [
        ("2026-08", 1),
        ("2026-09", 2),
    ]

    # 3. Exit reason breakdown
    exit_reasons_result = MagicMock()
    exit_reasons_result.all.return_value = [
        ("Career Growth", 2),
        ("Relocation", 1),
    ]

    # 4. Department exit breakdown
    department_exits_result = MagicMock()
    department_exits_result.all.return_value = [
        (1, "Engineering", 2),
        (2, "HR", 1),
    ]

    db.execute.side_effect = [
        exit_types_result,
        monthly_result,
        exit_reasons_result,
        department_exits_result,
    ]

    mock_db(db)

    try:
        response = client.get(URL)

        assert response.status_code == 200
        body = response.json()

        assert body["total_recorded_exits"] == 3

        assert body["exit_type_breakdown"] == [
            {"exit_type": "RESIGNATION", "count": 2},
            {"exit_type": "TERMINATION", "count": 1},
        ]

        assert body["exit_reason_breakdown"] == [
            {"exit_reason": "Career Growth", "count": 2},
            {"exit_reason": "Relocation", "count": 1},
        ]

        assert body["department_exit_breakdown"] == [
            {
                "department_id": 1,
                "department_name": "Engineering",
                "count": 2,
            },
            {
                "department_id": 2,
                "department_name": "HR",
                "count": 1,
            },
        ]

        assert body["monthly_exit_trends"] == [
            {"month": "2026-08", "count": 1},
            {"month": "2026-09", "count": 2},
        ]

        interviews = body["exit_interviews"]

        assert interviews["total_interviews"] == 2
        assert interviews["average_satisfaction"] == 7.5
        assert interviews["recommendation_responses"] == 2
        assert interviews["recommendation_yes"] == 1
        assert interviews["recommendation_percentage"] == 50.0

    finally:
        cleanup_overrides()


def test_exit_analytics_handles_empty_data():
    cleanup_overrides()

    db = MagicMock()

    # Scalar query results for an empty database.
    db.scalar.side_effect = [
        0,       # Total recorded exits
        0,       # Total interviews
        None,    # Average satisfaction
        0,       # Recommendation responses
        0,       # Yes responses
    ]

    # 1. Exit type breakdown
    exit_types_result = MagicMock()
    exit_types_result.all.return_value = []

    # 2. Monthly exit trends
    monthly_result = MagicMock()
    monthly_result.all.return_value = []

    # 3. Exit reason breakdown
    exit_reasons_result = MagicMock()
    exit_reasons_result.all.return_value = []

    # 4. Department exit breakdown
    department_exits_result = MagicMock()
    department_exits_result.all.return_value = []

    db.execute.side_effect = [
        exit_types_result,
        monthly_result,
        exit_reasons_result,
        department_exits_result,
    ]

    mock_db(db)

    try:
        response = client.get(URL)

        assert response.status_code == 200
        body = response.json()

        assert body["total_recorded_exits"] == 0
        assert body["exit_type_breakdown"] == []
        assert body["exit_reason_breakdown"] == []
        assert body["department_exit_breakdown"] == []
        assert body["monthly_exit_trends"] == []

        interviews = body["exit_interviews"]

        assert interviews["total_interviews"] == 0
        assert interviews["average_satisfaction"] is None
        assert interviews["recommendation_responses"] == 0
        assert interviews["recommendation_yes"] == 0
        assert interviews["recommendation_percentage"] is None

    finally:
        cleanup_overrides()
