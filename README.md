# Meraki to Snipe-IT Sync

This project imports device information from the Cisco Meraki Dashboard API and stores it as assets in a Snipe-IT instance. It can run as a standalone Python script or inside a Docker container that executes the sync on a schedule.

## Features

- Fetches all devices from a Meraki organization
- Creates missing categories and models in Snipe-IT
- Adds new assets or updates existing ones based on serial number or asset tag
- Docker image runs `main.py` every hour via cron

## Requirements

- Python 3.11+
- Access to Cisco Meraki and Snipe-IT APIs
- `.env` file containing the following keys:

```env
MERAKI_API_KEY=your-meraki-api-key
ORGANIZATION_ID=your-organization-id
SNIPE_IT_API_KEY=your-snipeit-token
SNIPE_IT_URL=https://snipeit.example.com
```

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Running locally

After creating a `.env` file, run:

```bash
python main.py
```

## Docker

Build the image and run it with your environment file:

```bash
sudo docker build -t merakitosnipeit-cron:latest .
docker run --env-file .env merakitosnipeit-cron:latest
```

The Docker container installs cron and schedules the sync hourly. Logs are written to `logs/cron.log` inside the container.

## Example environment file

See `.env.example` for the expected variables.
