from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from martialmatch_scraper import (ALLOWED_CLUBS, TIMEZONE, EventNotFoundError,
                                  ParticipantsNotFoundError,
                                  ScheduleNotFoundError,
                                  fetch_all_tournament_ids,
                                  get_participants_schedule)
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError
from pydantic import field_validator

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


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
    return {
        "clubs": [
            {"id": k, "display_name": v["display_name"]}
            for k, v in ALLOWED_CLUBS.items()
        ]
    }


@app.get("/api/server-time")
async def get_server_time():
    """Return current server time."""
    return {"timestamp": int(datetime.now().timestamp())}


@app.get("/api/participants")
async def get_participants(
    event_id: str = Query(..., description="Tournament event ID"),
    club_id: str = Query(..., description="Club ID from allowed clubs"),
) -> Dict[str, Any]:
    try:
        params = ParticipantRequest(event_id=event_id, club_id=club_id)
        schedule_per_day = get_participants_schedule(params.event_id, params.club_id)
        return {"schedule": schedule_per_day}
    except PydanticValidationError as e:
        error_msg = e.errors()[0]["msg"] if e.errors() else "Validation error"
        raise HTTPException(status_code=400, detail=error_msg)
    except (EventNotFoundError, ScheduleNotFoundError, ParticipantsNotFoundError) as e:
        return {"schedule": {}, "message": str(e)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=e.args[0] if e.args else str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


# Models for validation
class ParticipantRequest(BaseModel):
    event_id: str = Field(
        ..., min_length=1, max_length=100, description="Tournament event ID"
    )
    club_id: str = Field(
        ..., min_length=1, max_length=100, description="Club ID from allowed clubs"
    )

    @field_validator("event_id", "club_id")
    @classmethod
    def strip_value(cls, v: str) -> str:
        """Strip whitespace from input values."""
        return v.strip()

    @field_validator("club_id")
    @classmethod
    def validate_club_exists(cls, v: str) -> str:
        """Validate that the club exists in ALLOWED_CLUBS."""
        if v not in ALLOWED_CLUBS:
            raise ValueError(f"Club ID {v} is not in the allowed clubs list")
        return v
