# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

A FastAPI web app that scrapes [MartialMatch](https://martialmatch.com/pl/) to aggregate tournament schedules for a predefined list of BJJ clubs. It fetches participant lists and match schedules, merges them, and serves a single-page UI.

## Commands

**Local dev (from `app/webapp/`):**

```bash
fastapi dev main.py --port 8000
```

**Tests (from `app/webapp/`):**

```bash
python -m pytest tests/test_main.py -v
```

**Single test:**

```bash
python -m pytest tests/test_main.py::test_get_clubs -v
```

**Docker:**

```bash
docker-compose up -d --build
```

## Architecture

All application code lives in `app/webapp/`. There are only three Python modules:

- **`main.py`** — FastAPI app, route handlers, and input validation via Pydantic (`ParticipantRequest`). Imports everything it needs from `martialmatch_scraper.py`.
- **`martialmatch_scraper.py`** — Core scraping logic. Defines `ALLOWED_CLUBS` (hardcoded club list). Contains three cached fetch functions (`fetch_bjj_participants`, `fetch_bjj_schedule`, `fetch_tournament_ids`) using `TTLCache` via the `cache_with_ttl` decorator. The main entry point is `get_participants_schedule`, which fetches both data sources and calls `merge_participants_with_schedule` to join them on the `category` column using pandas.
- **`utils.py`** — Thin HTTP client wrapper (`make_api_request`) and `extract_numeric_id`. Raises `EventNotFoundHTTPError` on 404s, which `martialmatch_scraper.py` converts to `EventNotFoundError`.

**Caching:** Three separate `TTLCache` instances in `martialmatch_scraper.py` — participants (30 min), schedule (10 min), tournaments (60 min). The `cache_with_ttl` decorator key is `str(args) + str(kwargs)`.

**Data flow:** `GET /api/participants?event_id=&club_id=` → Pydantic validation → `get_participants_schedule` → two JSON API calls (`/starting-lists/public` and `/schedules`) → pandas merge → dict grouped by day returned as JSON.

**Adding a club:** Edit `ALLOWED_CLUBS` in `martialmatch_scraper.py`. The `academy` and `branch` fields must match exactly what the MartialMatch API returns; `display_name` is shown in the UI.

**Templates/static:** Jinja2 templates in `app/webapp/templates/`, static assets in `app/webapp/static/`. The frontend JS (`static/js/main.js`) calls the REST API and renders the schedule client-side.

## Formatting

Code is formatted with `black` and imports sorted with `isort`.
