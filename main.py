from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from bjj_participants_scraper import (
    fetch_bjj_participants,
    fetch_bjj_schedule,
    merge_participants_with_schedule,
    fetch_all_tournament_ids
)
from typing import Dict, Any

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


@app.get("/api/participants/{event_id}")
async def get_participants(event_id: str) -> Dict[str, Any]:
    try:
        participants = fetch_bjj_participants(event_id)
        if participants.empty:
            return {"schedule": {}}

        schedule = fetch_bjj_schedule(event_id)
        schedule_per_day = merge_participants_with_schedule(participants, schedule)
        return {"schedule": schedule_per_day}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))