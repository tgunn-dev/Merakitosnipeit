#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Meraki to Snipe-IT Sync Setup ===${NC}\n"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed or not in PATH${NC}"
    echo "Please install Python 3.8 or higher from https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ Found $PYTHON_VERSION${NC}\n"

# Ask user which setup mode they want
echo -e "${BLUE}Setup Mode:${NC}"
echo "1. Development (local, venv in current directory)"
echo "2. Production (systemd, venv in /opt/merakitosnipeit)"
echo ""
read -p "Choose setup mode (1 or 2): " -n 1 -r
echo
SETUP_MODE=$REPLY

if [ "$SETUP_MODE" == "1" ]; then
    SETUP_TYPE="development"
    VENV_DIR="venv"
    BASE_DIR="."
elif [ "$SETUP_MODE" == "2" ]; then
    SETUP_TYPE="production"
    echo ""
    read -p "Enter deployment path (default: /opt/merakitosnipeit): " CUSTOM_PATH
    BASE_DIR="${CUSTOM_PATH:-/opt/merakitosnipeit}"
    VENV_DIR="$BASE_DIR/venv"
else
    echo -e "${RED}Invalid choice. Exiting.${NC}"
    exit 1
fi

echo -e "${BLUE}Setup Type: $SETUP_TYPE${NC}\n"

# For production, check sudo access and create directory
if [ "$SETUP_TYPE" == "production" ]; then
    if [ "$BASE_DIR" != "." ] && [ ! -d "$BASE_DIR" ]; then
        echo "Creating deployment directory: $BASE_DIR"
        sudo mkdir -p "$BASE_DIR"
        if [ $? -ne 0 ]; then
            echo -e "${RED}Error: Failed to create directory. You may need sudo access.${NC}"
            exit 1
        fi
    fi

    # Copy project files to deployment directory if not already there
    if [ ! -f "$BASE_DIR/main.py" ]; then
        echo "Copying project files to $BASE_DIR..."
        SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
        sudo cp -r "$SCRIPT_DIR"/* "$BASE_DIR/" 2>/dev/null || true
        sudo cp -r "$SCRIPT_DIR"/.env.example "$BASE_DIR/" 2>/dev/null || true
        sudo cp -r "$SCRIPT_DIR"/.gitignore "$BASE_DIR/" 2>/dev/null || true
        echo -e "${GREEN}✓ Project files copied${NC}\n"
    fi

    # Create syncer user for systemd service
    if ! id syncer &>/dev/null; then
        echo "Creating syncer system user..."
        sudo useradd --system --home /nonexistent --shell /bin/false syncer 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Syncer user created${NC}\n"
        else
            echo -e "${YELLOW}⚠ Could not create syncer user (may already exist)${NC}\n"
        fi
    else
        echo -e "${GREEN}✓ Syncer user already exists${NC}\n"
    fi

    # Check if we need sudo for venv creation
    if [ ! -w "$BASE_DIR" ]; then
        echo -e "${YELLOW}Note: Using sudo for venv creation (requires sudo access)${NC}\n"
        USE_SUDO="sudo"
    else
        USE_SUDO=""
    fi
else
    USE_SUDO=""
fi

# Create virtual environment
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Virtual environment already exists at $VENV_DIR${NC}"
    read -p "Would you like to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing virtual environment..."
        $USE_SUDO rm -rf "$VENV_DIR"
    else
        echo "Using existing virtual environment"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR..."
    $USE_SUDO python3 -m venv "$VENV_DIR"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Virtual environment created${NC}\n"
    else
        echo -e "${RED}Error: Failed to create virtual environment${NC}"
        exit 1
    fi
fi

# For production with sudo, use venv python directly
if [ -n "$USE_SUDO" ]; then
    PYTHON_BIN="$VENV_DIR/bin/python3"
    PIP_BIN="$VENV_DIR/bin/pip"
else
    # Activate virtual environment for development
    echo "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Virtual environment activated${NC}\n"
    else
        echo -e "${RED}Error: Failed to activate virtual environment${NC}"
        exit 1
    fi
    PYTHON_BIN="python3"
    PIP_BIN="pip"
fi

# Upgrade pip
echo "Upgrading pip..."
if [ -n "$USE_SUDO" ]; then
    $USE_SUDO $PIP_BIN install --upgrade pip setuptools wheel > /dev/null 2>&1
else
    $PIP_BIN install --upgrade pip setuptools wheel > /dev/null 2>&1
fi

# Install dependencies
echo "Installing dependencies..."
REQUIREMENTS_FILE="$BASE_DIR/requirements.txt"
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    REQUIREMENTS_FILE="requirements.txt"
fi

if [ -n "$USE_SUDO" ]; then
    if $USE_SUDO $PIP_BIN install -r "$REQUIREMENTS_FILE" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Dependencies installed${NC}\n"
    else
        echo -e "${RED}Error: Failed to install dependencies${NC}"
        echo "Try running manually:"
        echo -e "  ${YELLOW}sudo $PIP_BIN install -r $REQUIREMENTS_FILE${NC}"
        exit 1
    fi
else
    if $PIP_BIN install -r "$REQUIREMENTS_FILE" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Dependencies installed${NC}\n"
    else
        echo -e "${RED}Error: Failed to install dependencies${NC}"
        exit 1
    fi
fi

# For production, setup .env and fix permissions
if [ "$SETUP_TYPE" == "production" ]; then
    # Check for .env file
    if [ ! -f "$BASE_DIR/.env" ]; then
        echo -e "${YELLOW}⚠ .env file not found at $BASE_DIR/.env${NC}"
        echo ""

        if [ -f ".env.example" ]; then
            read -p "Would you like to create .env from .env.example? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                $USE_SUDO cp .env.example "$BASE_DIR/.env"
                echo -e "${GREEN}✓ Created .env file${NC}"
                echo -e "${YELLOW}Please edit $BASE_DIR/.env and add your API keys:${NC}"
                echo "  - MERAKI_API_KEY"
                echo "  - ORGANIZATION_ID"
                echo "  - SNIPE_IT_API_KEY"
                echo "  - SNIPE_IT_URL"
            else
                echo -e "${YELLOW}Please create a .env file manually at $BASE_DIR/.env using .env.example as a template${NC}"
            fi
        fi
        echo ""
    else
        echo -e "${GREEN}✓ .env file found${NC}\n"
    fi

    # Fix permissions for systemd user
    echo "Setting up permissions for systemd service..."
    $USE_SUDO chown -R syncer:syncer "$BASE_DIR" 2>/dev/null || true
    $USE_SUDO chmod 600 "$BASE_DIR/.env" 2>/dev/null || true
    echo -e "${GREEN}✓ Permissions configured${NC}\n"
fi

# Display completion message
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "Setup Type: $SETUP_TYPE"
echo "Venv Location: $VENV_DIR"
if [ "$SETUP_TYPE" == "production" ]; then
    echo "Base Directory: $BASE_DIR"
fi
echo ""

if [ "$SETUP_TYPE" == "development" ]; then
    echo -e "${BLUE}Next steps (Development):${NC}"
    echo "1. Activate the virtual environment:"
    echo -e "   ${YELLOW}source venv/bin/activate${NC}"
    echo ""
    echo "2. Ensure your .env file is configured with:"
    echo "   - MERAKI_API_KEY"
    echo "   - ORGANIZATION_ID"
    echo "   - SNIPE_IT_API_KEY"
    echo "   - SNIPE_IT_URL"
    echo ""
    echo "3. Run the sync:"
    echo -e "   ${YELLOW}python main.py${NC}"
    echo ""
    echo "4. For scheduled runs, use APScheduler:"
    echo -e "   ${YELLOW}python scheduler.py --cron \"0 2 * * *\"${NC}"
    echo ""
else
    echo -e "${BLUE}Next steps (Production):${NC}"
    echo "1. Ensure your .env file is configured:"
    echo -e "   ${YELLOW}sudo nano $BASE_DIR/.env${NC}"
    echo ""
    echo "2. Install systemd service:"
    echo -e "   ${YELLOW}sudo cp merakitosnipeit.service /etc/systemd/system/${NC}"
    echo -e "   ${YELLOW}sudo cp merakitosnipeit.timer /etc/systemd/system/${NC}"
    echo ""
    echo "3. Enable and start the timer:"
    echo -e "   ${YELLOW}sudo systemctl daemon-reload${NC}"
    echo -e "   ${YELLOW}sudo systemctl enable merakitosnipeit.timer${NC}"
    echo -e "   ${YELLOW}sudo systemctl start merakitosnipeit.timer${NC}"
    echo ""
    echo "4. Check status:"
    echo -e "   ${YELLOW}sudo systemctl status merakitosnipeit.timer${NC}"
    echo -e "   ${YELLOW}sudo systemctl list-timers merakitosnipeit.timer${NC}"
    echo ""
fi

echo "For more information, see README.md and QUICKSTART.md"
