# Build stage: compile native extensions (numpy, pandas, pydantic-core, etc.)
FROM python:3.11-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY app/requirements-runtime.txt .
RUN pip install --no-cache-dir -r requirements-runtime.txt

# Runtime stage: clean image with no build tools
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

RUN adduser --disabled-password --gecos "" appuser

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY ./app/webapp/static /app/static
COPY ./app/webapp/templates /app/templates
COPY ./app/webapp/main.py /app/
COPY ./app/webapp/martialmatch_scraper.py /app/
COPY ./app/webapp/utils.py /app/

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--port", "8000", "--host", "0.0.0.0"]
