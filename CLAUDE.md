# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Meraki to Snipe-IT Sync** is a data integration tool that automatically synchronizes device information from Cisco Meraki Dashboard API to Snipe-IT asset management system. It can run as a standalone script or as a containerized cron job (hourly).

**Key Architecture:**
- **meraki_api.py**: Fetches all devices from Meraki organization
- **snipe_it.py**: Handles asset CRUD operations, category/model creation, and API retry logic with rate limiting
- **main.py**: Orchestrates the workflow—maps Meraki device data to Snipe-IT format and syncs

**Data Flow:** Meraki devices → Transform & map fields → Create/update Snipe-IT assets (idempotent via serial/asset tag deduplication)

## Essential Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run sync locally
python main.py

# Build Docker image
docker build -t merakitosnipeit-cron:latest .

# Run Docker container
docker run --env-file .env merakitosnipeit-cron:latest
```

## Configuration

Requires `.env` file with:
```env
MERAKI_API_KEY=<your-key>
ORGANIZATION_ID=<org-id>
SNIPE_IT_API_KEY=<your-token>
SNIPE_IT_URL=https://snipeit.example.com
```

See `.env.example` for template.

## Code Structure

**Minimal, flat codebase** (3 core files):
- **main.py** (58 lines): Entry point, orchestration, field mapping
- **meraki_api.py** (27 lines): Single function `device_details()` that initializes SDK and returns all devices
- **snipe_it.py** (160 lines): Key functions for asset/model/category management with retry logic

## Key Implementation Details

### API Retry & Rate Limiting
- `snipe_it.py` implements 429 (rate limit) retry with exponential backoff via `Retry-After` header
- Requests between devices: 0.5s delay
- Rate limiting is idempotent—retries don't create duplicates

### Asset Deduplication
- Looks for existing assets by serial number or asset tag before creating
- Updates if found, creates if not—ensures idempotency across multiple sync runs
- Serial number is mapped to Snipe-IT asset tag

### Data Mapping (main.py)
- Device product type → Category (auto-created if missing)
- Device model name → Model (auto-created if missing)
- Status always set to `status_id: 2`
- Notes field includes MAC address and network ID
- Field mapping occurs in `map_meraki_to_snipeit()` function

### API Authentication
- **Meraki**: Bearer token passed to SDK
- **Snipe-IT**: Bearer token in Authorization header

## Architecture Patterns

1. **Modular API clients**: Each API has its own module (single responsibility)
2. **Idempotent operations**: Safe to run multiple times without side effects
3. **Automatic entity creation**: Missing categories/models are created on-demand
4. **Rate limit awareness**: Implements backoff with proper HTTP status handling

## Testing

**Current state**: pytest installed but no tests exist. No test files or test configuration.

When adding tests, consider:
- Mocking Meraki and Snipe-IT API calls
- Testing data transformation in `map_meraki_to_snipeit()`
- Testing deduplication logic (existing asset lookup)
- Testing rate limit retry behavior

## Potential Enhancements

- Add structured logging (replace print statements)
- Add type hints to functions
- Validate all environment variables at startup
- Add dry-run mode for testing
- Consider async processing for large device counts
- Add metrics/monitoring hooks

## Deployment

**Docker** is the intended production deployment:
- Runs cron daemon in foreground
- Schedules `main.py` execution hourly via crontab
- Logs to `/app/logs/cron.log` inside container
- Uses `python:3.11-slim` base image

For local development, run `python main.py` directly after installing dependencies.
