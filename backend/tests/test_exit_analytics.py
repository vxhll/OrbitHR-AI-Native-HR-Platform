
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db.database import get_db
from app.main import app


client = TestClient(app)
URL = "/api/analytics/exits"


def cleanup_overrides():
    app.dependency_overrides.pop(get_db, None)


def mock_db(db):
    def get_test_db():
        yield db

    app.dependency_overrides[get_db] = get_test_db


def test_exit_analytics_returns_operational_exit_metrics():
    cleanup_overrides()

    db = MagicMock()
    db.scalar.side_effect = [
        3,       # Total recorded exits
        2,       # Total interviews
        7.5,     # Average satisfaction
        2,       # Recommendation responses
        1,       # Yes responses
    ]

    exit_types_result = MagicMock()
    exit_types_result.all.return_value = [
        ("RESIGNATION", 2),
        ("TERMINATION", 1),
    ]

    monthly_result = MagicMock()
    monthly_result.all.return_value = [
        ("2026-08", 1),
        ("2026-09", 2),
    ]

    db.execute.side_effect = [
        exit_types_result,
        monthly_result,
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
    db.scalar.side_effect = [0, 0, None, 0, 0]

    exit_types_result = MagicMock()
    exit_types_result.all.return_value = []

    monthly_result = MagicMock()
    monthly_result.all.return_value = []

    db.execute.side_effect = [
        exit_types_result,
        monthly_result,
    ]

    mock_db(db)

    try:
        response = client.get(URL)

        assert response.status_code == 200

        body = response.json()

        assert body["total_recorded_exits"] == 0
        assert body["exit_type_breakdown"] == []
        assert body["monthly_exit_trends"] == []

        interviews = body["exit_interviews"]
        assert interviews["total_interviews"] == 0
        assert interviews["average_satisfaction"] is None
        assert interviews["recommendation_responses"] == 0
        assert interviews["recommendation_yes"] == 0
        assert interviews["recommendation_percentage"] is None

    finally:
        cleanup_overrides()
