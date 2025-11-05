# MartialMatch schedule aggregator

[MartialMatch](https://martialmatch.com/pl/) competitions scraper. For chosen **competition** and **club** aggregates **competitors** and displays **schedule** for each day sorted by time, making it easier to follow your team's matches during tournaments.

## Why was this created?

When using MartialMatch during a competition:
- Finding competitors from your club requires browsing through multiple pages
- There is no aggregated view of all mats for a club - you need to filter each mat separately
- During large tournaments, the MartialMatch page can become slow

Therefore, I created this simple app that:
- Allows you to choose a competition and one of predefined clubs
- Shows all competitors from your club with their fight times and mat numbers
- Uses caching when fetching data from MartialMatch, making it resistant to traffic overload during large tournaments

## Developer Guide

### Prerequisites
- Docker and Docker Compose (recommended)
- Python 3.8+
- pip package manager

### Quick Start with Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/gregg127/martialmatch-scraper
cd martialmatch-scraper
```

2. Provide SSL certificates in `nginx/cert/` directory:
   - `server.crt` - SSL certificate  
   - `server.key` - Private key

3. Start the application:
```bash
docker-compose up -d --build
```

The application will be available at:
- HTTPS: `https://localhost` (requires SSL certificates in `nginx/cert/`)

### Local Development Setup (without nginx)

1. Clone the repository:
```bash
git clone https://github.com/gregg127/martialmatch-scraper
cd martialmatch-scraper
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r app/requirements.txt
```

4. Run the development server:
```bash
cd app/webapp
fastapi dev main.py --port 8080
```

The application will be available at `http://localhost:8080`

### Testing
Run the test suite:
```bash
cd app/webapp
python -m pytest tests/test_main.py -v
```

## Contributing
1. Fork the repository
2. Create a feature branch
3. Submit a pull request
