import pytest
from fastapi.testclient import TestClient
from main import app
from martialmatch_scraper import ALLOWED_CLUBS

client = TestClient(app)

def test_get_clubs():
    """Test the /api/clubs endpoint"""
    response = client.get("/api/clubs")
    assert response.status_code == 200
    data = response.json()
    assert "clubs" in data
    assert len(data["clubs"]) == len(ALLOWED_CLUBS)
    assert all("id" in club and "display_name" in club for club in data["clubs"])

@pytest.mark.parametrize("event_id,club_id,schedule_type,expected_status", [
    ("123", list(ALLOWED_CLUBS.keys())[0], "planned", 500),  # Valid request but non-existent event
    ("123", "invalid_club", "planned", 422),  # Invalid club validation
    ("", list(ALLOWED_CLUBS.keys())[0], "planned", 422),  # Empty event_id (query parameter)
    ("123", "", "planned", 422),  # Empty club_id (query parameter)
    ("x" * 101, list(ALLOWED_CLUBS.keys())[0], "planned", 422),  # Too long event_id
    ("123", "x" * 101, "planned", 422),  # Too long club_id
    ("123", list(ALLOWED_CLUBS.keys())[0], "", 422),  # Empty schedule_type
    ("123", list(ALLOWED_CLUBS.keys())[0], "invalid", 422),  # Invalid schedule_type
    ("123", list(ALLOWED_CLUBS.keys())[0], "real", 500),  # Valid schedule_type
])
def test_get_participants_validation(event_id, club_id, schedule_type, expected_status):
    """Test validation for /api/participants endpoint"""
    response = client.get(
        f"/api/participants", 
        params={"event_id": event_id, "club_id": club_id, "schedule_type": schedule_type}
    )
    assert response.status_code == expected_status

def test_get_tournaments():
    """Test the /api/tournaments endpoint"""
    response = client.get("/api/tournaments")
    assert response.status_code == 200
    data = response.json()
    assert "tournaments" in data
    assert isinstance(data["tournaments"], dict)
    assert "active" in data["tournaments"]
    assert "archived" in data["tournaments"]