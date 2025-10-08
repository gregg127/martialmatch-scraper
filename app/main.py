from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, ValidationError as PydanticValidationError

from martialmatch_scraper import (
    fetch_bjj_participants,
    fetch_bjj_schedule,
    merge_participants_with_schedule,
    fetch_all_tournament_ids,
    ALLOWED_CLUBS
)

app = FastAPI()

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


@app.get("/api/participants")
async def get_participants(
    event_id: str = Query(..., description="Tournament event ID"),
    club_id: str = Query(..., description="Club ID from allowed clubs"),
    schedule_type: str = Query(..., description="Type of schedule to fetch (planned or real)")
) -> Dict[str, Any]:
    try:
        params = ParticipantRequest(event_id=event_id, club_id=club_id, schedule_type=schedule_type)
        
        participants = fetch_bjj_participants(params.event_id, params.club_id)
        if participants.empty:
            return {"schedule": {}}

        schedule = fetch_bjj_schedule(event_id, schedule_type)
        schedule_per_day = merge_participants_with_schedule(participants, schedule)
        return {"schedule": schedule_per_day}

    except PydanticValidationError as e:
        error_msg = e.errors()[0]['msg'] if e.errors() else "Validation error"
        raise HTTPException(status_code=400, detail=error_msg)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=e.args[0] if e.args else str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

# Models for validation
class ParticipantRequest(BaseModel):
    event_id: str = Field(..., min_length=1, max_length=100, description="Tournament event ID")
    club_id: str = Field(..., min_length=1, max_length=100, description="Club ID from allowed clubs")
    schedule_type: str = Field(..., description="Type of schedule to fetch (planned or real)")

    @field_validator('event_id', 'club_id', 'schedule_type')
    @classmethod
    def strip_value(cls, v: str) -> str:
        """Strip whitespace from input values."""
        return v.strip()

    @field_validator('schedule_type')
    @classmethod
    def validate_schedule_type(cls, v: str) -> str:
        """Validate that schedule_type is either 'planned' or 'real'."""
        if v not in ['planned', 'real']:
            raise ValueError("Schedule type must be either 'planned' or 'real'")
        return v

    @field_validator('club_id')
    @classmethod
    def validate_club_exists(cls, v: str) -> str:
        """Validate that the club exists in ALLOWED_CLUBS."""
        from martialmatch_scraper import ALLOWED_CLUBS
        if v not in ALLOWED_CLUBS:
            raise ValueError(f'Club ID {v} is not in the allowed clubs list')
        return v