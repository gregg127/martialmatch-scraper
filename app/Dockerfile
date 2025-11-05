# Application Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create a non-root user
RUN adduser --disabled-password --gecos "" appuser

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary application files and directories
COPY ./app/webapp/static /app/static
COPY ./app/webapp/templates /app/templates
COPY ./app/webapp/main.py /app/
COPY ./app/webapp/martialmatch_scraper.py /app/
COPY ./app/webapp/utils.py /app/

# Change ownership of the app directory to appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8080

# Run the application with uvicorn on port 8080
CMD ["fastapi", "run", "main.py", "--port", "8080", "--host", "0.0.0.0"]