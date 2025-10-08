import pytest
from fastapi.testclient import TestClient
from main import app
from martialmatch_scraper import ALLOWED_CLUBS

# Test setup
client = TestClient(app)

# Test constants
MAX_FIELD_LENGTH = 100
VALID_CLUB_ID = list(ALLOWED_CLUBS.keys())[0]


# =============================================================================
# API Endpoint Tests
# =============================================================================

def test_get_clubs():
    """Test the /api/clubs endpoint
    
    Expected JSON response structure:
    {
        "clubs": [
            {
                "id": "test_club_id_1",
                "display_name": "Test Club Name 1"
            },
            {
                "id": "test_club_id_2", 
                "display_name": "Test Club Name 2"
            }
        ]
    }
    """
    response = client.get("/api/clubs")
    assert response.status_code == 200
    data = response.json()
    assert "clubs" in data
    assert len(data["clubs"]) == len(ALLOWED_CLUBS)
    
    # Verify each club has the expected structure and data types
    for club in data["clubs"]:
        assert "id" in club
        assert "display_name" in club
        assert isinstance(club["id"], str)
        assert isinstance(club["display_name"], str)
        assert club["id"] in ALLOWED_CLUBS  # Verify ID exists in allowed clubs

def test_get_tournaments():
    """Test the /api/tournaments endpoint
    
    Expected JSON response structure:
    {
        "tournaments": {
            "active": [
                {
                    "id": "123-tournament-name",
                    "name": "Tournament Name"
                },
                ...
            ],
            "archived": [
                {
                    "id": "456-old-tournament-name", 
                    "name": "Old Tournament Name"
                },
                ...
            ]
        }
    }
    """
    response = client.get("/api/tournaments")
    assert response.status_code == 200
    data = response.json()
    assert "tournaments" in data
    assert isinstance(data["tournaments"], dict)
    assert "active" in data["tournaments"]
    assert "archived" in data["tournaments"]
    
    # Verify structure of tournament lists
    for category in ["active", "archived"]:
        assert isinstance(data["tournaments"][category], list)
        # If tournaments exist, verify they have the expected structure
        for tournament in data["tournaments"][category]:
            assert "id" in tournament
            assert "name" in tournament
            assert isinstance(tournament["id"], str)
            assert isinstance(tournament["name"], str)


# =============================================================================
# API Validation Tests
# =============================================================================

@pytest.mark.parametrize("event_id,club_id,schedule_type,expected_status,test_case", [
    # Valid requests (but non-existent data)
    ("123", VALID_CLUB_ID, "planned", 500, "valid_request_nonexistent_event"),
    ("123", VALID_CLUB_ID, "real", 500, "valid_request_real_schedule"),
    
    # Invalid club validation
    ("123", "invalid_club", "planned", 422, "invalid_club_id"),
    
    # Empty parameter validation
    ("", VALID_CLUB_ID, "planned", 422, "empty_event_id"),
    ("123", "", "planned", 422, "empty_club_id"),
    ("123", VALID_CLUB_ID, "", 422, "empty_schedule_type"),
    
    # Field length validation
    ("x" * (MAX_FIELD_LENGTH + 1), VALID_CLUB_ID, "planned", 422, "event_id_too_long"),
    ("123", "x" * (MAX_FIELD_LENGTH + 1), "planned", 422, "club_id_too_long"),
    
    # Invalid enum values
    ("123", VALID_CLUB_ID, "invalid", 422, "invalid_schedule_type"),
])
def test_get_participants_validation(event_id, club_id, schedule_type, expected_status, test_case):
    """Test validation for /api/participants endpoint
    
    Expected JSON response structure for successful requests:
    {
        "schedule": {
            "Day 1": [
                {
                    "Imię i nazwisko": "Participant Name",
                    "Klub": "Club Name",
                    "Kategoria": "Category Name",
                    "Mata": "Mat Name",
                    "Szacowany czas": "10:00 - 10:30",
                    "Dzień": "Day 1"
                }
            ],
            "Day 2": [...]
        }
    }
    
    For empty results or no participants: {"schedule": {}}
    """
    response = client.get(
        f"/api/participants", 
        params={"event_id": event_id, "club_id": club_id, "schedule_type": schedule_type}
    )
    assert response.status_code == expected_status, f"Test case '{test_case}' failed"
