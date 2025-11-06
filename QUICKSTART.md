# Quick Start Guide

Get Meraki to Snipe-IT Sync up and running in minutes.

## Prerequisites

- Python 3.8 or higher
- Meraki API key and Organization ID
- Snipe-IT API token and URL

## 1-Minute Setup

### Using the setup script (macOS/Linux/Git Bash)

```bash
./setup.sh
```

The script will:
- ✓ Create a virtual environment
- ✓ Install all dependencies
- ✓ Prompt you to create `.env` file from template

### Using Make (if installed)

```bash
make setup
```

### Manual setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

## 2. Configure Your Credentials

Edit `.env` with your API keys:

```env
MERAKI_API_KEY=your-meraki-api-key-here
ORGANIZATION_ID=your-org-id-here
SNIPE_IT_API_KEY=your-snipeit-api-token-here
SNIPE_IT_URL=https://snipeit.example.com
```

**How to get credentials:**
- **Meraki API Key**: [Meraki Dashboard](https://account.meraki.com/login/dashboard_login) → Account → API
- **Organization ID**: Meraki Dashboard → Settings → Organization
- **Snipe-IT API Token**: Snipe-IT → Settings → API → Create New Token

## 3. Run Your First Sync

### Using the setup script's activation

```bash
source venv/bin/activate
python main.py
```

### Using Make

```bash
make run
```

### Manual execution

```bash
source venv/bin/activate
python main.py
```

## 4. Schedule Regular Syncs

### Option A: APScheduler (Recommended - All Platforms)

```bash
python scheduler.py
```

Runs sync every hour. See `scheduler.py` for customization.

### Option B: Systemd Timer (Linux Only)

```bash
# Copy service and timer files
sudo cp merakitosnipeit.service /etc/systemd/system/
sudo cp merakitosnipeit.timer /etc/systemd/system/

# Edit paths in service file if needed
sudo nano /etc/systemd/system/merakitosnipeit.service

# Enable and start timer
sudo systemctl daemon-reload
sudo systemctl enable merakitosnipeit.timer
sudo systemctl start merakitosnipeit.timer

# Check status
sudo systemctl status merakitosnipeit.timer
```

### Option C: Docker (All Platforms)

```bash
docker build -t merakitosnipeit:latest .
docker run --env-file .env merakitosnipeit:latest
```

## Troubleshooting

### Python not found
```bash
# Make sure Python 3.8+ is installed
python3 --version

# On macOS, use Homebrew
brew install python@3.11
```

### Virtual environment issues
```bash
# Remove and recreate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### API authentication errors
- Verify API keys in `.env` file
- Check Meraki and Snipe-IT URLs are accessible
- Ensure tokens haven't expired

### Rate limiting errors
The sync handles rate limits automatically with exponential backoff. If you see persistent 429 errors:
- Increase the delay between devices (edit `main.py`)
- Run during off-peak hours

## Common Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run sync once
python main.py

# Run scheduled sync
python scheduler.py

# List make commands
make help

# Clean up virtual environment
make clean
```

## Need Help?

- See [README.md](README.md) for full documentation
- Check [CLAUDE.md](CLAUDE.md) for architecture details
- Review [IMPROVEMENTS.md](IMPROVEMENTS.md) for recent changes
