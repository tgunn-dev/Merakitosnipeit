# Quick Start Guide

Get Meraki to Snipe-IT Sync up and running in minutes.

## Prerequisites

- Python 3.8 or higher
- Meraki API key and Organization ID
- Snipe-IT API token and URL

## Step 1: Run Setup Script

```bash
./setup.sh
```

The script will ask you to choose a setup mode.

---

## For Development (Local Testing)

### Step 2: Choose Development Mode

When prompted:
```
Setup Mode:
1. Development (local, venv in current directory)
2. Production (systemd, venv in /opt/merakitosnipeit)

Choose setup mode (1 or 2): 1
```

The script will:
- ✓ Create a virtual environment in `./venv`
- ✓ Install all dependencies
- ✓ Prompt you to create `.env` file from template

### Step 3: Configure Your Credentials

Edit `.env` with your API keys:

```bash
nano .env
```

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

### Step 4: Run Your First Sync

```bash
source venv/bin/activate
python main.py
```

### Step 5: Schedule Regular Syncs (Optional)

Run sync every day at 2 AM:

```bash
source venv/bin/activate
python scheduler.py --cron "0 2 * * *"
```

Or run every hour:

```bash
python scheduler.py
```

---

## For Production (Server Deployment)

### Step 2: Choose Production Mode

When prompted:
```
Setup Mode:
1. Development (local, venv in current directory)
2. Production (systemd, venv in /opt/merakitosnipeit)

Choose setup mode (1 or 2): 2
```

Enter deployment path (or press Enter for default `/opt/merakitosnipeit`).

The script will automatically:
- ✓ Create `/opt/merakitosnipeit` directory (with sudo if needed)
- ✓ **Copy all project files** from current directory
- ✓ Create virtual environment at `/opt/merakitosnipeit/venv`
- ✓ **Create `syncer` system user** for secure execution
- ✓ Install all dependencies in venv
- ✓ Set up `.env` file in deployment directory
- ✓ Fix permissions for systemd execution
- ✓ Copy systemd service and timer files to `/etc/systemd/system/`

### Step 3: Configure Your Credentials

The script will prompt you to create `.env`. Edit it with your API keys:

```bash
sudo nano /opt/merakitosnipeit/.env
```

Add:
```env
MERAKI_API_KEY=your-meraki-api-key-here
ORGANIZATION_ID=your-org-id-here
SNIPE_IT_API_KEY=your-snipeit-api-token-here
SNIPE_IT_URL=https://snipeit.example.com
```

### Step 4: Enable and Start Systemd Timer

```bash
sudo systemctl daemon-reload
sudo systemctl enable merakitosnipeit.timer
sudo systemctl start merakitosnipeit.timer
```

### Step 5: Verify It's Working

Check the timer is scheduled:
```bash
sudo systemctl list-timers merakitosnipeit.timer
```

Output should show next run at **02:00 (2 AM) daily**:
```
NEXT                        LEFT     LAST
Fri 2025-11-07 02:00:00 CST 9h      (none)
```

Test it immediately:
```bash
sudo systemctl start merakitosnipeit.service
```

View logs:
```bash
sudo journalctl -u merakitosnipeit.service -n 20 --no-pager
```

You should see sync output like:
```
Starting Meraki to Snipe-IT sync...
[1/63] Processing device: ...
✓ Successful: 63
Total API calls: ...
```

The sync will run automatically **every day at 2:00 AM** and survive server reboots.

---

## Troubleshooting

### Python not found

```bash
# Make sure Python 3.8+ is installed
python3 --version

# On macOS, use Homebrew
brew install python@3.11

# On Ubuntu/Debian
sudo apt-get install python3.11 python3.11-venv
```

### Virtual environment issues

```bash
# Development mode - remove and recreate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Production mode - remove and rerun setup.sh
sudo rm -rf /opt/merakitosnipeit/venv
./setup.sh  # Choose production mode
```

### API authentication errors

- Verify API keys in `.env` file
- Check Meraki and Snipe-IT URLs are accessible
- Ensure tokens haven't expired
- Wait 1-2 minutes if credentials were just created

### Sudo access required

For production mode, `setup.sh` may ask for your sudo password. This is safe—it only:
- Creates the deployment directory
- Creates the venv
- Sets permissions for the `syncer` user

---

## Scheduling Options

### Development: APScheduler

```bash
# Run every day at 2 AM
python scheduler.py --cron "0 2 * * *"

# Run every hour
python scheduler.py --interval 60

# Run every 30 minutes
python scheduler.py --interval 30

# Run once for testing
python scheduler.py --run-once
```

### Production: Systemd Timer

Done automatically by `setup.sh` in production mode. Runs daily at **2:00 AM**.

To change the time, edit:
```bash
sudo nano /etc/systemd/system/merakitosnipeit.timer
```

Change the `OnCalendar` line. Examples:
- `OnCalendar=*-*-* 02:00:00` → 2 AM daily
- `OnCalendar=*-*-* 14:00:00` → 2 PM daily
- `OnCalendar=*-*-* 00,12:00:00` → Midnight and noon

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart merakitosnipeit.timer
```

---

## Common Commands

### Development

```bash
# Activate virtual environment
source venv/bin/activate

# Run sync once
python main.py

# Run scheduled sync (daily at 2 AM)
python scheduler.py --cron "0 2 * * *"

# Deactivate virtual environment
deactivate
```

### Production

```bash
# View sync logs
sudo journalctl -u merakitosnipeit.service -f

# Check timer status
sudo systemctl status merakitosnipeit.timer

# Run sync manually (for testing)
sudo systemctl start merakitosnipeit.service

# Restart timer
sudo systemctl restart merakitosnipeit.timer

# Stop timer
sudo systemctl stop merakitosnipeit.timer
sudo systemctl disable merakitosnipeit.timer
```

---

## Need Help?

- See [README.md](README.md) for full documentation
- Check [CLAUDE.md](CLAUDE.md) for architecture details
- Review [IMPROVEMENTS.md](IMPROVEMENTS.md) for recent changes
