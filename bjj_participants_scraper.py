import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
import re
import pytz

def fetch_bjj_participants(event_id):
    """Fetch BJJ participants for the given event ID."""
    url = f"https://martialmatch.com/pl/events/{event_id}/starting-lists"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    
    participant_data = []
    categories = soup.find_all("div", class_="column is-offset-2 is-8")

    for i in range(0, len(categories), 2):
        category_section, table_section = categories[i], categories[i + 1] if i + 1 < len(categories) else None
        category = category_section.find("h4", class_="title is-4 is-marginless")
        if not category:
            raise ValueError("Category not found.")

        category_name = category.text.strip()
        if not table_section or not table_section.find("table"):
            raise ValueError(f"No table found for category: {category_name}")

        rows = table_section.find("tbody").find_all("tr")
        for row in rows:
            columns = row.find_all("td")
            name = columns[1].find("a", class_="competitor-name").text.strip()
            club_tag = columns[2].find("a")
            club_name = club_tag.text.strip()
            location = columns[2].text.replace(club_name, "").strip()
            club = f"{club_name} {location}".strip()
            participant_data.append((name, club, category_name))

    df = pd.DataFrame(participant_data, columns=["Imię i nazwisko", "Klub", "Kategoria"])
    return df[df["Klub"] == "Academia Gorila / Warszawa"]

def fetch_bjj_schedule(event_id):
    """Fetch BJJ competition schedule from the MartialMatch API."""
    numeric_id = re.search(r'\d+', event_id).group(0)
    url = f"https://martialmatch.com/api/events/{numeric_id}/schedules"
    cookies = {'PANEL_LANGUAGE_V3': 'pl', 'PANEL_TIMEZONE': 'Europe/Warsaw'}

    response = requests.get(url, headers={'Cookie': '; '.join(f'{k}={v}' for k, v in cookies.items())})
    response.raise_for_status()
    json_data = response.json()

    utc_tz = pytz.utc
    pl_tz = pytz.timezone('Europe/Warsaw')
    schedule_data = []

    for day in json_data["schedules"]:
        for mat in day["mats"]:
            for category in mat["categories"]:
                start = datetime.strptime(category['scheduledCategoryTime']['start'], '%Y-%m-%d %H:%M:%S')
                end = datetime.strptime(category['scheduledCategoryTime']['end'], '%Y-%m-%d %H:%M:%S')
                start_pl = utc_tz.localize(start).astimezone(pl_tz).strftime('%H:%M')
                end_pl = utc_tz.localize(end).astimezone(pl_tz).strftime('%H:%M')
                schedule_data.append([
                    category["name"],
                    mat["name"],
                    f"{start_pl} - {end_pl}",
                    day["name"]
                ])

    return pd.DataFrame(schedule_data, columns=["Kategoria", "Mata", "Szacowany czas", "Dzień"])

def fetch_tournament_ids(url):
    """Fetch tournament IDs from MartialMatch events page."""
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    
    tournament_ids = []
    for link in soup.find_all('a', href=re.compile(r'^/pl/events/\d+.*')):
        href = link.get('href')
        id_match = re.search(r'/pl/events/(\d+.*?)(?:/|$)', href)
        if id_match and id_match.group(1) not in [t["id"] for t in tournament_ids]:
            name = link.text.strip()
            if name:
                tournament_ids.append({"id": id_match.group(1), "name": name})
    
    return tournament_ids

def fetch_all_tournament_ids():
    """Fetch tournament IDs from both active and archive pages."""
    return {
        "active": fetch_tournament_ids("https://martialmatch.com/pl/events"),
        "archived": fetch_tournament_ids("https://martialmatch.com/pl/events/archive")
    }

def merge_participants_with_schedule(participants, schedule):
    """Merge participants data with schedule data and group by day."""
    schedule_per_day = {}
    if not schedule.empty:
        for day in schedule['Dzień'].unique():
            merged_data = pd.merge(participants, schedule[schedule['Dzień'] == day], on="Kategoria", how="inner")
            merged_data['start_time'] = merged_data['Szacowany czas'].str.extract(r'(\d{2}:\d{2}) -')
            merged_data = merged_data.sort_values('start_time')
            merged_data = merged_data.drop('start_time', axis=1)
            schedule_per_day[day] = merged_data.to_dict(orient='records')
    
    return schedule_per_day
