# Meraki to Snipe-IT Sync

**Automatically synchronize device inventory from Cisco Meraki Dashboard to Snipe-IT asset management.**

This tool seamlessly integrates your network infrastructure data, fetching all devices from your Meraki organization and creating/updating corresponding assets in Snipe-IT. Built for reliability with intelligent caching, rate-limit handling, and comprehensive logging.

## Features

✅ **Efficient API Usage**
- Smart caching minimizes API calls (load categories/models once at startup)
- Batch processing with 0.5s delays to respect rate limits
- Retry logic with exponential backoff for transient failures

✅ **Data Integrity**
- Automatic category and model creation from Meraki device types
- Idempotent operations—safe to run multiple times
- Deduplication by serial number or asset tag prevents duplicates

✅ **Flexible Scheduling**
- **APScheduler**: Python-based scheduler (recommended for all deployments)
- **Systemd timer**: Native Linux scheduler (recommended for servers)
- **Docker container**: Containerized deployment
- **Manual execution**: Run once with `python main.py`

✅ **Observability**
- Structured logging with timestamps and severity levels
- Detailed sync statistics (created, updated, failed counts)
- API call tracking and performance metrics
- Per-device success/failure reporting

## Architecture Overview

```
┌─────────────────┐
│ Meraki API      │
│ (Dashboard)     │
└────────┬────────┘
         │ [1 API call]
         │ Fetch all devices
         ▼
┌─────────────────────────────────────────────┐
│         Meraki to Snipe-IT Sync             │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │ 1. Initialize Cache (startup)        │   │
│  │    • Load all categories              │   │
│  │    • Load all models                  │   │
│  │    [2-4 API calls total]              │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │ 2. Process Each Device               │   │
│  │    • Map Meraki fields to Snipe-IT  │   │
│  │    • Look up in cache (no API call!) │   │
│  │    • Create if missing               │   │
│  │    • Update if exists                │   │
│  │    [1-2 API calls per device]         │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │ 3. Generate Statistics               │   │
│  │    • Track success/failure           │   │
│  │    • Measure performance             │   │
│  │    • Log API usage                   │   │
│  └──────────────────────────────────────┘   │
└────────┬────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ Snipe-IT API    │
│ Asset Database  │
└─────────────────┘
```

## Data Flow: Device Synchronization

```
Meraki Device Data                   Snipe-IT Asset
─────────────────────────────────────────────────────

name                   ─────────►  name
serial                 ───┬────►  asset_tag
                          └────►  serial (for dedup)

model                  ┐
                       ├──────►  model (auto-create)
productType            ┘

mac                    ──────►  notes
networkId              ──────►  notes
(purchase_date)        ──────►  purchase_date (if present)
(purchase_cost)        ──────►  purchase_cost (if present)

                                status_id: 2 (Ready to Deploy)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Category Hierarchy:
productType (e.g., "Camera", "Switch", "Appliance")
         ↓ (auto-created if missing)
    category (in Snipe-IT)
         ↓
    model (linked to category)
         ↓
    asset (device instance)
```

## API Efficiency

### Call Count Analysis

For a sync run with 100 devices using 5 unique models across 3 categories:

**Without Caching (Old Approach):**
- Fetch devices: 1 call
- Per device (100 × 5 ops): 500 calls
- **Total: ~501 API calls** ❌

**With Caching (Current Approach):**
- Fetch devices: 1 call
- Initialize cache: 2 calls (categories, models)
- Per device (100 × 1.2 ops): 120 calls
- **Total: ~123 API calls** ✅ **75% reduction!**

### Rate Limiting Strategy

- **Delay between devices**: 0.5 seconds (prevents overwhelming API)
- **Rate limit handling**: Exponential backoff using `Retry-After` header
- **Max retries**: 3 attempts per operation
- **Idempotent**: Safe to retry without creating duplicates

## Requirements

- **Python**: 3.11 or later
- **APIs**: Access to both Meraki and Snipe-IT instances
- **Environment**: `.env` file with credentials

## Configuration

Create a `.env` file in the project root:

```env
# Meraki Configuration
MERAKI_API_KEY=your-meraki-api-key-here
ORGANIZATION_ID=your-org-id-here

# Snipe-IT Configuration
SNIPE_IT_API_KEY=your-snipeit-api-token-here
SNIPE_IT_URL=https://snipeit.example.com
```

Get your credentials:
- **Meraki API Key**: [Meraki Dashboard](https://account.meraki.com/login/dashboard_login) → Account → API → Generate
- **Organization ID**: Meraki Dashboard → Settings → Organization
- **Snipe-IT API Token**: Snipe-IT Settings → API → Create New Token

See `.env.example` for a template.

## Installation

### Quick Start (Recommended)

We provide automated setup scripts to handle virtual environment creation and dependency installation:

**Option A: Using the setup script** (macOS/Linux/Git Bash)
```bash
./setup.sh
```

**Option B: Using Make** (if you have `make` installed)
```bash
make setup
make run
```

**Option C: Manual setup** (for advanced users)
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run once to test
python main.py
```

### Next Steps

After installation, ensure your `.env` file is configured with your API credentials (see [Configuration](#configuration) above), then proceed to [Usage](#usage).

## Usage

### Option 1: Manual Execution (Testing)

```bash
python main.py
```

Output example:
```
2025-01-15 14:23:45,123 - __main__ - INFO - Starting Meraki to Snipe-IT sync...
2025-01-15 14:23:46,456 - snipe_it - INFO - Initializing entity cache...
2025-01-15 14:23:47,789 - meraki_api - INFO - Successfully fetched 42 devices from Meraki
[1/42] Processing device: Switch-01
✓ Successfully synced device: Switch-01
...
============================================================
SYNC SUMMARY
============================================================
Total devices processed: 42
  ✓ Successful: 41
  ✗ Failed: 1
  → Created: 5
  ↻ Updated: 36
Duration: 38.45 seconds
============================================================
```

### Option 2: APScheduler (Recommended for All Deployments)

Run every hour:
```bash
python scheduler.py
```

With custom interval (every 30 minutes):
```bash
python scheduler.py --interval 30
```

With cron expression (run at noon and midnight):
```bash
python scheduler.py --cron "0 0,12 * * *"
```

Run once and exit (useful for testing):
```bash
python scheduler.py --run-once
```

### Option 3: Systemd Timer (Linux Servers)

Install the service and timer:
```bash
# Copy files to system
sudo cp merakitosnipeit.service /etc/systemd/system/
sudo cp merakitosnipeit.timer /etc/systemd/system/

# Create user and directory
sudo useradd -m -s /bin/bash syncer
sudo mkdir -p /opt/merakitosnipeit
sudo cp -r ./* /opt/merakitosnipeit/
sudo chown -R syncer:syncer /opt/merakitosnipeit

# Install dependencies
cd /opt/merakitosnipeit
sudo -u syncer pip install -r requirements.txt

# Enable and start timer
sudo systemctl daemon-reload
sudo systemctl enable merakitosnipeit.timer
sudo systemctl start merakitosnipeit.timer

# Check status
sudo systemctl status merakitosnipeit.timer
sudo journalctl -u merakitosnipeit.service -f
```

### Option 4: Docker Container

Build the image:
```bash
docker build -t merakitosnipeit:latest .
```

Run with APScheduler (hourly):
```bash
docker run -d \
  --name merakitosnipeit \
  --env-file .env \
  --restart unless-stopped \
  merakitosnipeit:latest \
  python scheduler.py --interval 60
```

Run once:
```bash
docker run --rm --env-file .env merakitosnipeit:latest python main.py
```

## Development

### Running Tests

```bash
pytest -v
```

### Logging Levels

Control logging detail via environment variable:
```bash
LOGLEVEL=DEBUG python main.py  # Verbose logging
LOGLEVEL=WARNING python main.py  # Only warnings and errors
```

### Dry Run Mode

Test without making API calls:
```bash
python main.py --dry-run
```

## Troubleshooting

### Rate Limit Errors

If you see "Rate limit exceeded" messages:
- Increase the delay between devices in `main.py` (line 141)
- Reduce the sync frequency (increase interval)
- Check Snipe-IT API rate limits in admin settings

### Missing Devices

Verify in Meraki Dashboard:
- Organization ID is correct
- API key has read permissions
- Network has devices

### API Authentication Failed

- Double-check credentials in `.env`
- Verify Snipe-IT URL includes protocol (https://)
- Ensure API tokens haven't expired

## Performance Metrics

Typical sync times (per 100 devices):
- **Cache initialization**: 2-3 seconds
- **Meraki fetch**: 3-5 seconds
- **Processing**: 50-120 seconds (depends on network and API latency)
- **Total**: ~1-2 minutes

Factors affecting performance:
- Number of devices
- Number of unique models/categories
- Network latency to APIs
- Snipe-IT server performance

## Deployment Recommendations

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| **Linux Server** | Systemd Timer | Native, reliable, no overhead |
| **Cloud VM** | APScheduler | Portable, easy to containerize |
| **Kubernetes** | CronJob | Native orchestration |
| **Docker Desktop** | APScheduler | Simple, self-contained |
| **Testing** | Manual (`python main.py`) | Quick feedback loop |

## Architecture & Design

- **Modular**: Separate Meraki, Snipe-IT, and orchestration logic
- **Idempotent**: Safe to run multiple times—no side effects
- **Cacheable**: Minimizes API calls with smart caching
- **Resilient**: Retries transient failures, continues on per-device errors
- **Observable**: Comprehensive logging and statistics

## Future Enhancements

- [ ] Async API calls for faster processing
- [ ] Database backend for state persistence
- [ ] Multi-organization support
- [ ] Custom field mapping configuration
- [ ] Webhook notifications on sync completion
- [ ] Prometheus metrics endpoint

## License

MIT

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review logs: `grep ERROR /var/log/sync.log`
3. Run in debug mode: `LOGLEVEL=DEBUG python main.py`
4. Open an issue on GitHub
