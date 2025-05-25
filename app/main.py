# Standard library imports
from typing import Dict, Any

# Third-party imports
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, ValidationError as PydanticValidationError

# Local imports
from martialmatch_scraper import (
    fetch_bjj_participants,
    fetch_bjj_schedule,
    merge_participants_with_schedule,
    fetch_all_tournament_ids,
    ALLOWED_CLUBS
)

app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/tournaments")
async def get_tournaments():
    tournaments = fetch_all_tournament_ids()
    if not tournaments:
        raise HTTPException(status_code=500, detail="Failed to fetch tournament IDs")
    return {"tournaments": tournaments}


@app.get("/api/clubs")
async def get_clubs():
    """Return all allowed clubs."""
    return {"clubs": [{"id": k, "display_name": v["display_name"]} for k, v in ALLOWED_CLUBS.items()]}


@app.get("/api/participants/{event_id}")
async def get_participants(
    event_id: str = Path(..., description="Tournament event ID"),
    club_id: str = Query(..., description="Club ID from allowed clubs")
) -> Dict[str, Any]:
    try:
        params = ParticipantRequest(event_id=event_id, club_id=club_id)
        
        participants = fetch_bjj_participants(params.event_id, params.club_id)
        if participants.empty:
            return {"schedule": {}}

        schedule = fetch_bjj_schedule(event_id)
        schedule_per_day = merge_participants_with_schedule(participants, schedule)
        return {"schedule": schedule_per_day}

    except PydanticValidationError:
        raise HTTPException(status_code=422, detail="Validation error")
    except ValueError:
        raise HTTPException(status_code=400, detail="Validation error")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

# Models for validation
class ParticipantRequest(BaseModel):
    event_id: str = Field(..., min_length=1, max_length=100, description="Tournament event ID")
    club_id: str = Field(..., min_length=1, max_length=100, description="Club ID from allowed clubs")

    @field_validator('event_id', 'club_id')
    @classmethod
    def strip_value(cls, v: str) -> str:
        """Strip whitespace from input values."""
        return v.strip()

    @field_validator('club_id')
    @classmethod
    def validate_club_exists(cls, v: str) -> str:
        """Validate that the club exists in ALLOWED_CLUBS."""
        from martialmatch_scraper import ALLOWED_CLUBS
        if v not in ALLOWED_CLUBS:
            raise ValueError(f'Club ID {v} is not in the allowed clubs list')
        return v