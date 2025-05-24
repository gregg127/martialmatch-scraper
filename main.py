from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from bjj_participants_scraper import (
    fetch_bjj_participants,
    fetch_bjj_schedule,
    merge_participants_with_schedule
)
import re
from typing import Dict, Any

app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/bjj-participants")
async def get_bjj_participants(url: str) -> Dict[str, Any]:
    try:
        # Fetch BJJ Participants
        participants = fetch_bjj_participants(url)
        if participants.empty:
            print("No participants found.")
            exit(0)

        # Fetch BJJ Schedule and merge with participants
        event_id = re.search(r'(?<=/events/)(\d+)', url).group(1)
        schedule = fetch_bjj_schedule(event_id)
        
        schedule_per_day = merge_participants_with_schedule(participants, schedule)

        return {"schedule": schedule_per_day}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))