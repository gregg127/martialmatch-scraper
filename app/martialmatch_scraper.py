from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
from cachetools import TTLCache
from functools import wraps
import pytz

from utils import extract_numeric_id, make_api_request, EventNotFoundHTTPError


# Error messages
NO_PARTICIPANTS_MESSAGE = "Nie znaleziono zawodników tego klubu w tym turnieju"
NO_SCHEDULE_MESSAGE = "Brak harmonogramu wskazanego typu dla tego turnieju"
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
PARTICIPANTS_CACHE_TTL = 1800   # Cache time in seconds (30 minutes)
SCHEDULE_CACHE_TTL = 600        # Cache time in seconds (10 minutes)
TOURNAMENTS_CACHE_TTL = 3600    # Cache time in seconds (60 minutes)
CACHE_SIZE = 50                 # Maximum number of items in cache
TIMEZONE = pytz.timezone('Europe/Warsaw')
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

ALLOWED_CLUBS = {
    "academia_gorila_warszawa": {
        "name": "Academia Gorila / Warszawa",
        "display_name": "Academia Gorila (Warszawa)"
    },
    "academia_gorila_ruda_slaska": {
        "name": "Academia Gorila / Ruda Śląska",
        "display_name": "Academia Gorila (Ruda Śląska)"
    },
    "academia_gorila_bielsko_biala": {
        "name": "Academia Gorila / Bielsko Biała",
        "display_name": "Academia Gorila (Bielsko Biała)"
    },
}

ALLOWED_SCHEDULE_TYPES = {
    'planned': {
        'name': 'planned',
        'description': 'Scheduled time'
    },
    'real': {
        'name': 'real', 
        'description': 'Real-time schedule'
    }
}

participants_cache = TTLCache(maxsize=CACHE_SIZE, ttl=PARTICIPANTS_CACHE_TTL)
schedule_cache = TTLCache(maxsize=CACHE_SIZE, ttl=SCHEDULE_CACHE_TTL)
tournaments_cache = TTLCache(maxsize=CACHE_SIZE, ttl=TOURNAMENTS_CACHE_TTL)

def cache_with_ttl(cache):
    """Time-based cache decorator."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            result = cache.get(key)
            if result is None:
                result = func(*args, **kwargs)
                cache[key] = result
            return result
        return wrapper
    return decorator

@cache_with_ttl(participants_cache)
def fetch_bjj_participants(event_id, club_id):
    """
    Fetch BJJ participants for the given event ID and club.
    Results are cached to reduce API calls.
    
    Args:
        event_id: ID of the tournament
        club_id: ID of the club from ALLOWED_CLUBS dictionary
    """
    if club_id not in ALLOWED_CLUBS:
        raise ValueError(f"Club {club_id} is not in the allowed clubs list")
    url = f"{BASE_URL}/pl/events/{event_id}/starting-lists"
    try:
        response = make_api_request(url)
        soup = BeautifulSoup(response.text, "html.parser")
    except EventNotFoundHTTPError:
        raise EventNotFoundError()
    except Exception:
        raise  # Re-raise other exceptions as-is
    participant_data = []
    categories = soup.find_all("div", class_="column is-offset-2 is-8")

    for i in range(0, len(categories), 2):
        try:
            category_section = categories[i]
            table_section = categories[i + 1] if i + 1 < len(categories) else None
            
            category_name = category_section.find("h4", class_="title is-4 is-marginless").text.strip()
            
            if not table_section or not table_section.find("table"):
                continue  # Skip categories without participants instead of raising error

            for row in table_section.find("tbody").find_all("tr"):
                cols = row.find_all("td")
                name = cols[1].find("a", class_="competitor-name").text.strip()
                club_tag = cols[2].find("a")
                club = f"{club_tag.text.strip()} {cols[2].text.replace(club_tag.text.strip(), '').strip()}".strip()
                participant_data.append((name, club, category_name))

        except (AttributeError, IndexError) as e:
            continue  # Skip malformed data instead of failing

    df = pd.DataFrame(participant_data, columns=["Imię i nazwisko", "Klub", "Kategoria"])
    return df[df["Klub"] == ALLOWED_CLUBS[club_id]["name"]]

@cache_with_ttl(schedule_cache)
def fetch_bjj_schedule(event_id, schedule_type):
    """
    Fetch BJJ competition schedule from the MartialMatch API.
    Results are cached to reduce API calls.

    Args:
        event_id: ID of the tournament
        schedule_type: 'planned' for scheduled time, 'real' for real-time schedule
    """
    numeric_id = extract_numeric_id(event_id)
    url = f"{BASE_URL}/api/events/{numeric_id}/schedules"
    cookies = {'PANEL_LANGUAGE_V3': 'pl', 'PANEL_TIMEZONE': 'Europe/Warsaw'}

    json_data = make_api_request(url, cookies).json()
    schedule_data = []
    
    for day in json_data.get("schedules", []):
        
        if schedule_type == ALLOWED_SCHEDULE_TYPES['real']['name'] and day.get("sharing") != 3:
            # Skip days that are not part of the real-time schedule
            continue
        
        for mat in day.get("mats", []):
            for category in mat.get("categories", []):
                try:
                    times = category.get("scheduledCategoryTime", {})
                    start_time = datetime.strptime(times["start"], DATE_FORMAT)
                    end_time = datetime.strptime(times["end"], DATE_FORMAT)
                    
                    # Convert to Polish timezone
                    start_time = start_time.replace(tzinfo=pytz.UTC).astimezone(TIMEZONE)
                    end_time = end_time.replace(tzinfo=pytz.UTC).astimezone(TIMEZONE)
                    
                    start = start_time.strftime('%H:%M')
                    end = end_time.strftime('%H:%M')
                    
                    schedule_data.append([
                        category["name"],
                        mat["name"],
                        f"{start} - {end}",
                        day["name"]
                    ])
                except (KeyError, ValueError):
                    continue  # Skip invalid time data

    return pd.DataFrame(schedule_data, columns=["Kategoria", "Mata", "Szacowany czas", "Dzień"])


def fetch_all_tournament_ids():
    """Fetch tournament IDs from both active and archive pages."""
    return {
        "active": fetch_tournament_ids(f"{BASE_URL}/pl/events"),
        "archived": fetch_tournament_ids(f"{BASE_URL}/pl/events/archive")
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
    
    for link in soup.find_all('a', href=re.compile(r'^/pl/events/\d+.*')):
        href = link.get('href')
        id_match = re.search(r'/pl/events/(\d+.*?)(?:/|$)', href)
        
        if id_match and id_match.group(1) not in seen_ids:
            name = link.text.strip()
            if name:
                tournament_id = id_match.group(1)
                seen_ids.add(tournament_id)
                tournament_ids.append({"id": tournament_id, "name": name})
    
    return tournament_ids


def get_participants_schedule(event_id, club_id, schedule_type):
    """
    Get participants schedule for a specific event, club, and schedule type.
    
    Args:
        event_id: ID of the tournament
        club_id: ID of the club from ALLOWED_CLUBS dictionary
        schedule_type: 'planned' for scheduled time, 'real' for real-time schedule
        
    Returns:
        Dict containing schedule organized by day, or empty dict if no participants
    """
    participants = fetch_bjj_participants(event_id, club_id)
    if participants.empty:
        raise ParticipantsNotFoundError()

    schedule = fetch_bjj_schedule(event_id, schedule_type)
    if schedule.empty:
        raise ScheduleNotFoundError()
    
    return merge_participants_with_schedule(participants, schedule)


def merge_participants_with_schedule(participants, schedule):
    """Merge participants data with schedule data and group by day."""
 
    schedule_per_day = {}
    for day in schedule['Dzień'].unique():
        day_schedule = schedule[schedule['Dzień'] == day]
        merged = pd.merge(participants, day_schedule, on="Kategoria", how="inner")
        
        if not merged.empty:
            merged['start_time'] = merged['Szacowany czas'].str.extract(r'(\d{2}:\d{2}) -')
            merged = merged.sort_values('start_time').drop('start_time', axis=1)
            schedule_per_day[day] = merged.to_dict(orient='records')
    
    return schedule_per_day
