import logging
import re
import time
from datetime import datetime
from functools import wraps

import pandas as pd
import pytz
from bs4 import BeautifulSoup
from cachetools import TTLCache
from utils import EventNotFoundHTTPError, extract_numeric_id, make_api_request

logger = logging.getLogger(__name__)

NO_PARTICIPANTS_MESSAGE = "Nie znaleziono zawodników tego klubu w tym turnieju"
NO_SCHEDULE_MESSAGE = "Brak harmonogramu dla tego turnieju"
EVENT_NOT_FOUND_MESSAGE = "Nie znaleziono turnieju"


class ScheduleNotFoundError(Exception):
    """Raised when no schedule data is available for the requested event."""

    def __init__(self, message=NO_SCHEDULE_MESSAGE):
        super().__init__(message)


class ParticipantsNotFoundError(Exception):
    """Raised when no participants are found for the requested club and event."""

    def __init__(self, message=NO_PARTICIPANTS_MESSAGE):
        super().__init__(message)


class EventNotFoundError(Exception):
    """Raised when the requested event does not exist (404 error)."""

    def __init__(self, message=EVENT_NOT_FOUND_MESSAGE):
        super().__init__(message)


BASE_URL = "https://martialmatch.com"
PARTICIPANTS_CACHE_TTL = 1800  # Cache time in seconds (30 minutes)
SCHEDULE_CACHE_TTL = 600  # Cache time in seconds (10 minutes)
TOURNAMENTS_CACHE_TTL = 3600  # Cache time in seconds (60 minutes)
CACHE_SIZE = 50  # Maximum number of items in cache
TIMEZONE = pytz.timezone("Europe/Warsaw")
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
API_COOKIES = {"PANEL_LANGUAGE_V3": "pl", "PANEL_TIMEZONE": "Europe/Warsaw"}

ALLOWED_CLUBS = {
    "academia_gorila_warszawa": {
        "academy": "Academia Gorila",
        "branch": "Warszawa",
        "display_name": "Academia Gorila (Warszawa)",
    },
    "academia_gorila_ruda_slaska": {
        "academy": "Academia Gorila",
        "branch": "Ruda Śląska",
        "display_name": "Academia Gorila (Ruda Śląska)",
    },
    "academia_gorila_bielsko_biala": {
        "academy": "Academia Gorila",
        "branch": "Bielsko Biała",
        "display_name": "Academia Gorila (Bielsko Biała)",
    },
}

participants_cache = TTLCache(maxsize=CACHE_SIZE, ttl=PARTICIPANTS_CACHE_TTL)
schedule_cache = TTLCache(maxsize=CACHE_SIZE, ttl=SCHEDULE_CACHE_TTL)
tournaments_cache = TTLCache(maxsize=CACHE_SIZE, ttl=TOURNAMENTS_CACHE_TTL)


def cache_with_ttl(cache):
    """Time-based cache decorator with logging for HIT/MISS."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            result = cache.get(key)
            if result is not None:
                logger.info(f"[CACHE HIT] {func.__name__} key={key}")
                return result
            logger.info(f"[CACHE MISS] {func.__name__} key={key}")
            result = func(*args, **kwargs)
            cache[key] = result
            return result

        return wrapper

    return decorator


@cache_with_ttl(participants_cache)
def _fetch_participants_json(event_id):
    """Fetch and cache the raw starting-lists JSON for an event."""
    numeric_id = extract_numeric_id(event_id)
    url = f"{BASE_URL}/api/events/{numeric_id}/starting-lists/public"
    try:
        return make_api_request(url, API_COOKIES).json()
    except EventNotFoundHTTPError:
        raise EventNotFoundError()


def fetch_bjj_participants(event_id, academy, branch=""):
    json_data = _fetch_participants_json(event_id)
    start_time_prof = time.time()
    participant_data = []
    for cat in json_data.get("categories", []):
        category_name = cat.get("category", "")
        for comp in cat.get("competitors", []):
            if comp.get("academy") == academy and (
                not branch or comp.get("branch", "").strip() == branch
            ):
                name = f"{comp['firstName']} {comp['lastName']}"
                participant_data.append((name, category_name))
    df = pd.DataFrame(participant_data, columns=["name", "category"])
    logger.info(
        f"[PROFILE] fetch_bjj_participants data parsing took {time.time() - start_time_prof:.4f} seconds"
    )
    return df


@cache_with_ttl(schedule_cache)
def fetch_bjj_schedule(event_id):
    numeric_id = extract_numeric_id(event_id)
    url = f"{BASE_URL}/api/events/{numeric_id}/schedules"
    json_data = make_api_request(url, API_COOKIES).json()
    start_time_prof = time.time()
    schedule_data = []
    for day in json_data.get("schedules", []):
        for mat in day.get("mats", []):
            for category in mat.get("categories", []):
                try:
                    times = category.get("scheduledCategoryTime", {})
                    start_time = datetime.strptime(times["start"], DATE_FORMAT)
                    end_time = datetime.strptime(times["end"], DATE_FORMAT)
                    start_time_tz = start_time.replace(tzinfo=pytz.UTC).astimezone(
                        TIMEZONE
                    )
                    end_time_tz = end_time.replace(tzinfo=pytz.UTC).astimezone(TIMEZONE)
                    start = start_time_tz.strftime("%H:%M")
                    end = end_time_tz.strftime("%H:%M")
                    start_timestamp = int(start_time_tz.timestamp())
                    end_timestamp = int(end_time_tz.timestamp())
                    schedule_data.append(
                        [
                            category["name"],
                            mat["name"],
                            day["name"],
                            f"{start} - {end}",
                            start_timestamp,
                            end_timestamp,
                        ]
                    )
                except (KeyError, ValueError):
                    continue
    df = pd.DataFrame(
        schedule_data,
        columns=[
            "category",
            "mat",
            "day",
            "time",
            "start_timestamp",
            "end_timestamp",
        ],
    )
    logger.info(
        f"[PROFILE] fetch_bjj_schedule data parsing took {time.time() - start_time_prof:.4f} seconds"
    )
    return df


def fetch_event_clubs(event_id):
    json_data = _fetch_participants_json(event_id)
    seen = set()
    clubs = []
    for cat in json_data.get("categories", []):
        for comp in cat.get("competitors", []):
            academy = comp.get("academy", "").strip()
            branch = comp.get("branch", "").strip()
            if not academy:
                continue
            key = (academy, branch)
            if key not in seen:
                seen.add(key)
                display = f"{academy} ({branch})" if branch else academy
                clubs.append(
                    {"academy": academy, "branch": branch, "display_name": display}
                )
    clubs.sort(key=lambda c: c["display_name"].lower())
    return clubs


def fetch_all_tournament_ids():
    """Fetch tournament IDs from both active and archive pages."""
    return {
        "active": fetch_tournament_ids(f"{BASE_URL}/pl/events"),
        "archived": fetch_tournament_ids(f"{BASE_URL}/pl/events/archive"),
    }


@cache_with_ttl(tournaments_cache)
def fetch_tournament_ids(url):
    """
    Fetch tournament IDs from MartialMatch events page.
    Results are cached to reduce API calls.
    """
    soup = BeautifulSoup(make_api_request(url).text, "html.parser")
    tournament_ids = []
    seen_ids = set()
    for link in soup.find_all("a", href=re.compile(r"^/pl/events/\d+.*")):
        href = link.get("href")
        id_match = re.search(r"/pl/events/(\d+.*?)(?:/|$)", href)
        if id_match and id_match.group(1) not in seen_ids:
            name = link.text.strip()
            if name:
                tournament_id = id_match.group(1)
                seen_ids.add(tournament_id)
                tournament_ids.append({"id": tournament_id, "name": name})
    return tournament_ids


def get_participants_schedule(event_id, academy, branch=""):
    participants = fetch_bjj_participants(event_id, academy, branch)
    if participants.empty:
        raise ParticipantsNotFoundError()
    schedule = fetch_bjj_schedule(event_id)
    if schedule.empty:
        raise ScheduleNotFoundError()
    return merge_participants_with_schedule(participants, schedule)


def merge_participants_with_schedule(participants, schedule):
    """Merge participants data with schedule data and group by day."""
    schedule_per_day = {}
    start_time_prof = time.time()
    schedule = schedule.copy()
    schedule["start_time"] = schedule["time"].str.extract(r"(\d{2}:\d{2}) -")
    merged = pd.merge(participants, schedule, on="category", how="inner")
    if merged.empty:
        logger.info(
            f"[PROFILE] merge_participants_with_schedule with empty merge took {time.time() - start_time_prof:.4f} seconds"
        )
        return schedule_per_day
    merged = merged.sort_values(["day", "start_time", "name"])
    merged = merged.drop("start_time", axis=1)
    for day, group in merged.groupby("day"):
        schedule_per_day[day] = group.to_dict(orient="records")
    logger.info(
        f"[PROFILE] merge_participants_with_schedule took {time.time() - start_time_prof:.4f} seconds"
    )
    return schedule_per_day
