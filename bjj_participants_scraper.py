import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
import re
import sys
import pytz


def fetch_bjj_participants(url):
    """Fetch BJJ participants from the given URL."""
    response = requests.get(f"{url}/starting-lists")
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
            name_tag = columns[1].find("a", class_="competitor-name")
            name = name_tag.text.strip() if name_tag else "Unknown Name"

            club_tag = columns[2].find("a")
            club_name = club_tag.text.strip() if club_tag else "Unknown Club"
            location = columns[2].text.replace(club_name, "").strip()
            club = f"{club_name} {location}".strip()

            participant_data.append((name, club, category_name))

    df = pd.DataFrame(participant_data, columns=["Imię i nazwisko", "Klub", "Kategoria"])

    # Filter participants based on the club name conditions
    academia_gorila_warszawa = df[df["Klub"] == "Academia Gorila / Warszawa"]
    df = df[~df.index.isin(academia_gorila_warszawa.index)]
    # academia_gorila = df[df["Klub"].str.startswith("Academia Gorila", na=False)]
    # df = df[~df.index.isin(academia_gorila.index)]
    # academia = df[df["Klub"].str.startswith("Academia", na=False) & ~df["Klub"].str.contains("Shaka", na=False)]

    # return pd.concat([academia_gorila_warszawa, academia_gorila, academia])
    return academia_gorila_warszawa


def fetch_bjj_schedule(event_id):
    """Fetch BJJ competition schedule from the MartialMatch API and convert times to Polish time."""
    cookies = {
        'PANEL_LANGUAGE_V3': 'pl',
        'PANEL_TIMEZONE': 'Europe/Warsaw'
    }
    cookie_header = '; '.join(f'{key}={value}' for key, value in cookies.items())
    url = f"https://martialmatch.com/api/events/{event_id}/schedules"

    response = requests.get(url, headers={'Cookie': cookie_header})
    response.raise_for_status()

    json_data = response.json()

    utc_tz = pytz.utc
    pl_tz = pytz.timezone('Europe/Warsaw')

    schedule_data = []

    for day in json_data["schedules"]:
        for mat in day["mats"]:
            for category in mat["categories"]:
                start_time_utc = datetime.strptime(category['scheduledCategoryTime']['start'], '%Y-%m-%d %H:%M:%S')
                end_time_utc = datetime.strptime(category['scheduledCategoryTime']['end'], '%Y-%m-%d %H:%M:%S')

                # Assign UTC timezone
                start_time_utc = utc_tz.localize(start_time_utc)
                end_time_utc = utc_tz.localize(end_time_utc)

                # Convert to Polish time
                start_time_pl = start_time_utc.astimezone(pl_tz).strftime('%H:%M')
                end_time_pl = end_time_utc.astimezone(pl_tz).strftime('%H:%M')

                schedule_data.append([
                    category["name"],
                    mat["name"],
                    f"{start_time_pl} - {end_time_pl}",
                    day["name"]
                ])
    return pd.DataFrame(schedule_data, columns=["Kategoria", "Mata", "Szacowany czas", "Dzień"])


def merge_participants_with_schedule(participants, schedule):
    """Merge participants data with schedule data and group by day."""
    schedule_per_day = {}
    if schedule.empty:
        return schedule_per_day
    
    for day in schedule['Dzień'].unique():
        # First merge the data
        merged_data = pd.merge(participants, schedule[schedule['Dzień'] == day], on="Kategoria", how="inner")
        
        # Extract start time and sort after merging
        merged_data['start_time'] = merged_data['Szacowany czas'].str.extract(r'(\d{2}:\d{2}) -')
        merged_data = merged_data.sort_values('start_time')
        
        # Remove the temporary start_time column
        merged_data = merged_data.drop('start_time', axis=1)
        schedule_per_day[day] = merged_data.to_dict(orient='records')
    
    return schedule_per_day
