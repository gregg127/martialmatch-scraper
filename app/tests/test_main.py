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

@pytest.mark.parametrize("event_id,club_id,expected_status", [
    ("123", list(ALLOWED_CLUBS.keys())[0], 500),  # Valid request but non-existent event
    ("123", "invalid_club", 422),  # Invalid club validation
    ("", list(ALLOWED_CLUBS.keys())[0], 404),  # Empty event_id (path parameter)
    ("123", "", 422),  # Empty club_id (query parameter)
    ("x" * 101, list(ALLOWED_CLUBS.keys())[0], 422),  # Too long event_id
    ("123", "x" * 101, 422),  # Too long club_id
])
def test_get_participants_validation(event_id, club_id, expected_status):
    """Test validation for /api/participants endpoint"""
    response = client.get(f"/api/participants/{event_id}", params={"club_id": club_id})
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