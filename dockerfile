# Use official Python runtime as base image (slim variant for smaller image size)
FROM python:3.11-slim

# Set working directory for all subsequent commands
WORKDIR /app

# Install system dependencies (cron for scheduling)
# Combined with cleanup to reduce layer size
RUN apt-get update && \
    apt-get install -y --no-install-recommends cron && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better Docker layer caching
# This way, dependencies are only reinstalled if requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create logs directory for cron output
RUN mkdir -p /app/logs

# Copy application code
COPY . /app

# Configure cron job to run sync script hourly
# The cron job runs main.py every hour at minute 0 and logs output to cron.log
RUN echo "0 * * * * /usr/local/bin/python /app/main.py >> /app/logs/cron.log 2>&1" > /etc/cron.d/merakitosnipeit && \
    chmod 0644 /etc/cron.d/merakitosnipeit && \
    crontab /etc/cron.d/merakitosnipeit && \
    touch /app/logs/cron.log

# Run cron daemon in foreground (required for Docker containers)
# This keeps the container running and executes cron jobs as scheduled
CMD ["cron", "-f"]

