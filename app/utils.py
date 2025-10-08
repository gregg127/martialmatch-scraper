import re
import requests


def extract_numeric_id(event_id):
    """Extract numeric ID from event identifier."""
    match = re.search(r'\d+', str(event_id))
    if not match:
        raise ValueError(f"Invalid event ID format for input: {event_id}")
    return match.group(0)


def make_api_request(url, cookies=None):
    """Make an API request."""
    try:
        response = requests.get(
            url, 
            headers={'Cookie': '; '.join(f'{k}={v}' for k, v in (cookies or {}).items())}
        )
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch data from {url}: {str(e)}")