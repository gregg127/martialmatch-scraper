from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from main import app
from martialmatch_scraper import (ALLOWED_CLUBS, participants_cache,
                                  schedule_cache, tournaments_cache)
from utils import EventNotFoundHTTPError

client = TestClient(app)
MAX_EVENT_ID_LENGTH = 100
MAX_ACADEMY_LENGTH = 200
MAX_BRANCH_LENGTH = 200

VALID_ACADEMY = list(ALLOWED_CLUBS.values())[0]["academy"]
VALID_BRANCH = list(ALLOWED_CLUBS.values())[0]["branch"]

MOCK_PARTICIPANTS_JSON = {
    "categories": [
        {
            "category": "adult; kobiety; -58 kg",
            "competitors": [
                {
                    "firstName": "Anna",
                    "lastName": "Testowa",
                    "academy": "Academia Gorila",
                    "branch": "Warszawa",
                }
            ],
        }
    ]
}

MOCK_SCHEDULE_JSON = {
    "schedules": [
        {
            "name": "Dzień 1",
            "mats": [
                {
                    "name": "Mata 1",
                    "categories": [
                        {
                            "name": "adult; kobiety; -58 kg",
                            "scheduledCategoryTime": {
                                "start": "2024-01-01 10:00:00",
                                "end": "2024-01-01 10:30:00",
                            },
                        }
                    ],
                }
            ],
        }
    ]
}

MOCK_TOURNAMENTS_HTML = '<a href="/pl/events/123-test-tournament">Test Tournament</a>'


def _make_response(json_data=None, text=""):
    mock = MagicMock()
    mock.json.return_value = json_data or {}
    mock.text = text
    return mock


def _mock_api(url, cookies=None):
    if "starting-lists" in url:
        return _make_response(json_data=MOCK_PARTICIPANTS_JSON)
    if "schedules" in url:
        return _make_response(json_data=MOCK_SCHEDULE_JSON)
    return _make_response(text=MOCK_TOURNAMENTS_HTML)


@pytest.fixture(autouse=True)
def clear_caches():
    participants_cache.clear()
    schedule_cache.clear()
    tournaments_cache.clear()


def test_get_clubs():
    response = client.get("/api/clubs")
    assert response.status_code == 200
    data = response.json()
    assert len(data["clubs"]) == len(ALLOWED_CLUBS)
    for club in data["clubs"]:
        assert "id" in club and "display_name" in club
        assert "academy" in club and "branch" in club
        assert club["id"] in ALLOWED_CLUBS


def test_get_tournaments():
    with patch("martialmatch_scraper.make_api_request", side_effect=_mock_api):
        response = client.get("/api/tournaments")
    assert response.status_code == 200
    tournaments = response.json()["tournaments"]
    for category in ["active", "archived"]:
        assert isinstance(tournaments[category], list)
        for t in tournaments[category]:
            assert "id" in t and "name" in t


def test_get_participants_returns_merged_schedule():
    with patch("martialmatch_scraper.make_api_request", side_effect=_mock_api):
        response = client.get(
            "/api/participants",
            params={
                "event_id": "123",
                "academy": VALID_ACADEMY,
                "branch": VALID_BRANCH,
            },
        )
    assert response.status_code == 200
    schedule = response.json()["schedule"]
    assert "Dzień 1" in schedule
    item = schedule["Dzień 1"][0]
    assert item["name"] == "Anna Testowa"
    assert item["category"] == "adult; kobiety; -58 kg"
    assert item["mat"] == "Mata 1"
    assert "time" in item
    assert "start_timestamp" in item
    assert "end_timestamp" in item


def test_get_participants_no_matching_competitors():
    def mock_no_competitors(url, cookies=None):
        if "starting-lists" in url:
            return _make_response(json_data={"categories": []})
        return _make_response(json_data=MOCK_SCHEDULE_JSON)

    with patch(
        "martialmatch_scraper.make_api_request", side_effect=mock_no_competitors
    ):
        response = client.get(
            "/api/participants",
            params={
                "event_id": "123",
                "academy": VALID_ACADEMY,
                "branch": VALID_BRANCH,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["schedule"] == {}
    assert "message" in data


def test_get_participants_event_not_found():
    with patch(
        "martialmatch_scraper.make_api_request", side_effect=EventNotFoundHTTPError
    ):
        response = client.get(
            "/api/participants",
            params={
                "event_id": "999999",
                "academy": VALID_ACADEMY,
                "branch": VALID_BRANCH,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["schedule"] == {}
    assert "message" in data


@pytest.mark.parametrize(
    "event_id,academy,branch",
    [
        ("", VALID_ACADEMY, VALID_BRANCH),
        ("123", "", ""),
        ("x" * (MAX_EVENT_ID_LENGTH + 1), VALID_ACADEMY, VALID_BRANCH),
        ("123", "x" * (MAX_ACADEMY_LENGTH + 1), ""),
        ("123", VALID_ACADEMY, "x" * (MAX_BRANCH_LENGTH + 1)),
    ],
    ids=[
        "empty_event_id",
        "empty_academy",
        "event_id_too_long",
        "academy_too_long",
        "branch_too_long",
    ],
)
def test_get_participants_returns_400_for_invalid_input(event_id, academy, branch):
    response = client.get(
        "/api/participants",
        params={"event_id": event_id, "academy": academy, "branch": branch},
    )
    assert response.status_code == 400
