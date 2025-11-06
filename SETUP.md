# Setup Guide: Meraki to Snipe-IT Sync

Complete step-by-step instructions for deploying the sync solution in various environments.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Local Development](#local-development)
4. [Production Deployments](#production-deployments)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- **Python**: 3.11 or later
- **OS**: Linux, macOS, or Windows
- **Network**: Outbound HTTPS access to Meraki and Snipe-IT APIs
- **Disk Space**: ~100MB for application + logs

### API Access
You'll need credentials for:
1. **Cisco Meraki Dashboard**
   - Organization with devices
   - Read-only API access recommended

2. **Snipe-IT Instance**
   - Admin or Asset manager role
   - API access enabled

## Environment Configuration

### Step 1: Get API Credentials

**Meraki:**
1. Login to [Meraki Dashboard](https://dashboard.meraki.com)
2. Go to **My Account** → **API**
3. Click **Generate API key**
4. Copy the key (keep it safe!)
5. From Dashboard, find your **Organization ID** in Settings

**Snipe-IT:**
1. Login to your Snipe-IT instance
2. Go to **Settings** → **API**
3. Click **Create New Token**
4. Set expiration (recommend 1 year+)
5. Copy the token
6. Note your Snipe-IT URL (e.g., `https://snipeit.company.com`)

### Step 2: Create `.env` File

```bash
# Navigate to project directory
cd /path/to/merakitosnipeit

# Copy template
cp .env.example .env

# Edit with your credentials
nano .env
```

**Contents of `.env`:**
```env
# Meraki Configuration
MERAKI_API_KEY=your-actual-api-key-here
ORGANIZATION_ID=your-actual-org-id-here

# Snipe-IT Configuration
SNIPE_IT_API_KEY=your-actual-token-here
SNIPE_IT_URL=https://snipeit.company.com

# Optional: Logging level (DEBUG, INFO, WARNING, ERROR)
# LOGLEVEL=INFO
```

**Security Note:**
- Never commit `.env` to version control
- Use different tokens for each deployment
- Rotate tokens annually
- Restrict API key/token permissions to minimum required

### Step 3: Verify Configuration

```bash
python3 -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('✓ MERAKI_API_KEY:', 'set' if os.getenv('MERAKI_API_KEY') else 'NOT SET')
print('✓ ORGANIZATION_ID:', 'set' if os.getenv('ORGANIZATION_ID') else 'NOT SET')
print('✓ SNIPE_IT_API_KEY:', 'set' if os.getenv('SNIPE_IT_API_KEY') else 'NOT SET')
print('✓ SNIPE_IT_URL:', os.getenv('SNIPE_IT_URL', 'NOT SET'))
"
```

---

## Local Development

### Quick Start (5 minutes)

```bash
# 1. Clone/navigate to project
cd ~/projects/merakitosnipeit

# 2. Create Python virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create and configure .env file (see above)
cp .env.example .env
# Edit .env with your credentials

# 5. Test the sync (one-time run)
python3 main.py

# You should see output like:
# 2025-01-15 14:23:45,123 - __main__ - INFO - Starting Meraki to Snipe-IT sync...
# [1/42] Processing device: Switch-01
# ✓ Successfully synced device: Switch-01
# ...
# ============================================================
# SYNC SUMMARY
# ============================================================
```

### Development Workflow

```bash
# Run with debug logging
LOGLEVEL=DEBUG python3 main.py

# Run scheduler in foreground (easy to stop with Ctrl+C)
python3 scheduler.py --run-once

# Run every 30 minutes (test interval)
python3 scheduler.py --interval 30

# Run with cron syntax
python3 scheduler.py --cron "*/15 * * * *"  # Every 15 minutes
```

### Code Structure

```
merakitosnipeit/
├── main.py              # Core sync logic, orchestration
├── meraki_api.py        # Meraki API client
├── snipe_it.py          # Snipe-IT API client with caching
├── scheduler.py         # APScheduler wrapper
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
├── README.md            # User documentation
├── SETUP.md             # This file
├── CLAUDE.md            # Claude Code guidelines
├── merakitosnipeit.service  # Systemd service file
└── merakitosnipeit.timer    # Systemd timer file
```

---

## Production Deployments

Choose the deployment method that best fits your infrastructure:

### Option A: Linux Server with Systemd Timer (RECOMMENDED)

**Best for:** On-premises servers, high reliability

**Steps:**

```bash
# 1. Create dedicated user
sudo useradd -m -s /bin/bash merakisync

# 2. Create application directory
sudo mkdir -p /opt/merakitosnipeit
cd /opt/merakitosnipeit

# 3. Clone/copy application files
sudo git clone <repo-url> .
# OR: sudo cp -r ~/merakitosnipeit/* .

# 4. Set permissions
sudo chown -R merakisync:merakisync /opt/merakitosnipeit
sudo chmod 750 /opt/merakitosnipeit

# 5. Install dependencies
sudo -u merakisync python3 -m venv venv
sudo -u merakisync venv/bin/pip install -r requirements.txt

# 6. Configure environment
sudo nano /opt/merakitosnipeit/.env
# Add your Meraki and Snipe-IT credentials
sudo chmod 600 /opt/merakitosnipeit/.env

# 7. Install systemd files
sudo cp merakitosnipeit.service /etc/systemd/system/
sudo cp merakitosnipeit.timer /etc/systemd/system/

# 8. Enable and start
sudo systemctl daemon-reload
sudo systemctl enable merakitosnipeit.timer
sudo systemctl start merakitosnipeit.timer

# 9. Verify it's running
sudo systemctl status merakitosnipeit.timer
sudo journalctl -u merakitosnipeit.service -f
```

**Monitoring:**
```bash
# View logs
sudo journalctl -u merakitosnipeit.service -n 50  # Last 50 lines

# Follow in real-time
sudo journalctl -u merakitosnipeit.service -f

# Check next run time
sudo systemctl list-timers merakitosnipeit.timer

# Manually trigger a run
sudo systemctl start merakitosnipeit.service
```

**Customizing Schedule:**
Edit `/etc/systemd/system/merakitosnipeit.timer`:
```ini
# Run every 30 minutes instead of hourly
OnCalendar=*:0/30
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart merakitosnipeit.timer
```

---

### Option B: Docker Container

**Best for:** Cloud deployments, Kubernetes, containerized workflows

**Using APScheduler (simple, self-contained):**

```bash
# 1. Build image
docker build -t merakitosnipeit:latest .

# 2. Run continuously with scheduler
docker run -d \
  --name merakitosnipeit \
  --env-file .env \
  --restart unless-stopped \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  merakitosnipeit:latest \
  python scheduler.py --interval 60

# 3. Check logs
docker logs -f merakitosnipeit

# 4. Test manually first
docker run --rm --env-file .env merakitosnipeit:latest python main.py
```

**For Kubernetes CronJob:**

Create `cronjob.yaml`:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: merakitosnipeit-sync
spec:
  schedule: "0 * * * *"  # Every hour
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: sync
            image: merakitosnipeit:latest
            command: ["python", "main.py"]
            envFrom:
            - secretRef:
                name: merakitosnipeit-secrets
          restartPolicy: OnFailure
```

Deploy:
```bash
kubectl apply -f cronjob.yaml
```

---

### Option C: Cloud Platform (AWS, Azure, GCP)

**AWS Lambda:**
```python
# handler.py
def lambda_handler(event, context):
    import main
    # Lambda uses environment variables for credentials
    exec(open('main.py').read())
    return {"statusCode": 200}
```

CloudWatch Events triggers the Lambda every hour.

**Google Cloud Functions:**
```python
def sync_devices(request):
    import main
    exec(open('main.py').read())
    return "Sync completed", 200
```

Cloud Scheduler triggers the function.

---

## Verification

### Test 1: Configuration Validation

```bash
python3 << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()

required = ['MERAKI_API_KEY', 'ORGANIZATION_ID', 'SNIPE_IT_API_KEY', 'SNIPE_IT_URL']
missing = [var for var in required if not os.getenv(var)]

if missing:
    print(f"❌ Missing: {', '.join(missing)}")
    exit(1)
else:
    print("✅ All credentials configured")
EOF
```

### Test 2: API Connectivity

```bash
python3 << 'EOF'
from meraki_api import device_details
from snipe_it import _get_headers, SNIPE_IT_URL
import requests

try:
    print("Testing Meraki API...")
    devices = device_details()
    print(f"✅ Meraki: Found {len(devices) if devices else 0} devices")
except Exception as e:
    print(f"❌ Meraki: {e}")

try:
    print("Testing Snipe-IT API...")
    headers = _get_headers()
    resp = requests.get(f"{SNIPE_IT_URL}/api/v1/status", headers=headers)
    if resp.status_code == 200:
        print("✅ Snipe-IT: Connected")
    else:
        print(f"❌ Snipe-IT: HTTP {resp.status_code}")
except Exception as e:
    print(f"❌ Snipe-IT: {e}")
EOF
```

### Test 3: Dry Run

```bash
# Run once without scheduler
python3 main.py

# Check output for:
# - ✓ Successfully synced device: [device names]
# - SYNC SUMMARY showing created/updated counts
```

### Test 4: Scheduler Test

```bash
# APScheduler - run once
python3 scheduler.py --run-once

# APScheduler - 1 minute interval (quick test)
timeout 120 python3 scheduler.py --interval 1

# Should show job starting/completing messages
```

---

## Troubleshooting

### Issue: "MERAKI_API_KEY not set"

**Cause**: `.env` file not found or not in correct location

**Solution**:
```bash
# Verify .env exists in current directory
ls -la .env

# Set variables manually for testing
export MERAKI_API_KEY="your-key-here"
export ORGANIZATION_ID="your-org-id"
export SNIPE_IT_API_KEY="your-token"
export SNIPE_IT_URL="https://snipeit.example.com"

python3 main.py
```

---

### Issue: "Rate limit exceeded"

**Cause**: API calls too fast, hitting rate limits

**Solution**:
- Increase delay in `main.py` line 141 (default 0.5s)
- Reduce sync frequency
- Check rate limits in Snipe-IT admin settings

```python
# In main.py, increase delay
time.sleep(1.0)  # Changed from 0.5
```

---

### Issue: "No devices found in Meraki"

**Cause**: Organization ID incorrect, or no devices in network

**Solution**:
```bash
# Verify organization ID
python3 << 'EOF'
from meraki_api import device_details, organization_id
print(f"Organization ID: {organization_id}")
devices = device_details()
print(f"Devices: {len(devices)}")
EOF

# Check Meraki Dashboard
# - Verify correct organization selected
# - Ensure networks have devices
# - Check API key permissions (read-only is fine)
```

---

### Issue: "Failed to create asset"

**Cause**: Model/category creation failed, or invalid field values

**Solution**:
```bash
# Run with debug logging
LOGLEVEL=DEBUG python3 main.py

# Check:
# - Model and category names are valid
# - Required Snipe-IT fields are present
# - No special characters in names that Snipe-IT rejects
```

---

### Issue: "Connection timeout"

**Cause**: Network/firewall blocking API calls

**Solution**:
```bash
# Test connectivity
python3 << 'EOF'
import requests
from snipe_it import SNIPE_IT_URL

try:
    resp = requests.get(f"{SNIPE_IT_URL}/api/v1/status", timeout=5)
    print(f"✅ Snipe-IT reachable: {resp.status_code}")
except requests.exceptions.ConnectionError as e:
    print(f"❌ Cannot reach {SNIPE_IT_URL}")
    print(f"Error: {e}")
EOF

# Check:
# - SNIPE_IT_URL is correct (includes https://)
# - Firewall allows outbound HTTPS
# - Proxy settings if needed
```

---

### Issue: "Permission denied" (Systemd)

**Cause**: User/file permissions incorrect

**Solution**:
```bash
# Fix ownership
sudo chown -R merakisync:merakisync /opt/merakitosnipeit
sudo chmod 750 /opt/merakitosnipeit
sudo chmod 600 /opt/merakitosnipeit/.env

# Verify permissions
ls -la /opt/merakitosnipeit/
ls -la /opt/merakitosnipeit/.env
```

---

## Getting Help

1. **Check logs**
   ```bash
   # Systemd
   sudo journalctl -u merakitosnipeit.service -n 100

   # Docker
   docker logs merakitosnipeit -n 100

   # Manual run
   python3 main.py 2>&1 | tee sync.log
   ```

2. **Enable debug logging**
   ```bash
   LOGLEVEL=DEBUG python3 main.py
   ```

3. **Verify configuration**
   ```bash
   python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('MERAKI_API_KEY', 'NOT SET')[:10])"
   ```

4. **Test APIs directly**
   ```bash
   # Meraki
   python3 -c "from meraki_api import device_details; print(len(device_details()))"

   # Snipe-IT
   python3 -c "import requests; from snipe_it import SNIPE_IT_URL, _get_headers; print(requests.get(f'{SNIPE_IT_URL}/api/v1/status', headers=_get_headers()).status_code)"
   ```

---

## Next Steps

After initial setup:

1. **Monitor first sync**: Watch logs to ensure devices are created/updated correctly
2. **Verify in Snipe-IT**: Login and confirm devices appear with correct information
3. **Set up log aggregation**: Collect logs from systemd/Docker for long-term monitoring
4. **Schedule backup**: Regular database backups if self-hosted
5. **Plan token rotation**: Set calendar reminder to rotate API tokens annually

---

## Support Resources

- [Meraki API Documentation](https://developer.cisco.com/meraki/api/)
- [Snipe-IT API Documentation](https://snipe-it.readme.io/reference)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Systemd Timer Documentation](https://man.archlinux.org/man/systemd.timer.5)
