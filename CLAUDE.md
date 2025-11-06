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

### Setup (Automated)
```bash
# Interactive setup script (asks for development or production mode)
./setup.sh

# Development mode: creates ./venv, run manually or with APScheduler
source venv/bin/activate
python main.py

# Production mode: copies files, creates syncer user, installs systemd
# (run ./setup.sh and choose option 2)
sudo systemctl daemon-reload
sudo systemctl enable merakitosnipeit.timer
sudo systemctl start merakitosnipeit.timer
```

### Manual Commands
```bash
# Install dependencies (requires venv already created)
pip install -r requirements.txt

# Run sync once
python main.py

# View production sync logs
sudo journalctl -u merakitosnipeit.service -n 20

# Check scheduled execution time
sudo systemctl list-timers merakitosnipeit.timer

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

**Minimal, flat codebase** (3 core files + setup/deployment files):

**Core Modules:**
- **main.py** (~180 lines): Entry point, SyncStatistics class, orchestration, field mapping, device processing loop
- **meraki_api.py** (~40 lines): Single function `device_details()` that initializes SDK and returns all devices
- **snipe_it.py** (~340 lines): Functions for asset/model/category CRUD, caching, deduplication, retry logic with rate limiting

**Setup & Deployment:**
- **setup.sh** (~230 lines): Interactive setup script for development and production modes
- **scheduler.py** (~170 lines): APScheduler wrapper for interval and cron-based scheduling
- **merakitosnipeit.service**: Systemd service unit file (oneshot type)
- **merakitosnipeit.timer**: Systemd timer for daily execution at 2:00 AM
- **Makefile** (~50 lines): Convenient make targets for local development
- **requirements.txt**: Python dependencies (meraki, requests, python-dotenv, APScheduler, pytest)

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

## Recent Improvements (November 2025)

- ✅ **Dual-mode setup script**: Development and production modes with automatic user/permission setup
- ✅ **Automatic file copying**: Production setup copies code from repo to deployment directory
- ✅ **Syncer user creation**: Setup automatically creates system user for secure systemd execution
- ✅ **API call tracking**: Fixed statistics to accurately track create/update/search operations
- ✅ **Systemd timer**: Daily execution at 2:00 AM with boot recovery (Persistent=true)
- ✅ **Documentation**: QUICKSTART.md, enhanced README.md, and setup automation
- ✅ **Error recovery**: Better error handling in setup and service execution

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

### Production: Systemd (Recommended)
- **Mode**: `./setup.sh` → choose production (2)
- **Execution**: Daily at 2:00 AM via systemd timer
- **User**: `syncer` (system user, auto-created by setup)
- **Auto-start**: Enabled on boot, survives reboots
- **Files**: `/opt/merakitosnipeit/` (or custom path)
- **Service**: `/etc/systemd/system/merakitosnipeit.{service,timer}`
- **Logs**: Via `journalctl -u merakitosnipeit.service`

### Development: Local Testing
- **Mode**: `./setup.sh` → choose development (1)
- **Execution**: Manual with `python main.py` or APScheduler
- **Files**: Current directory with `./venv`
- **Logs**: Console output and optional logging

### Docker (Alternative)
- Build: `docker build -t merakitosnipeit:latest .`
- Run: `docker run --env-file .env merakitosnipeit:latest`
- Logs: Container stderr/stdout
