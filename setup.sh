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

# Create virtual environment
VENV_DIR="venv"
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Virtual environment already exists at ./$VENV_DIR${NC}"
    read -p "Would you like to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        echo "Using existing virtual environment"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Virtual environment created${NC}\n"
    else
        echo -e "${RED}Error: Failed to create virtual environment${NC}"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Virtual environment activated${NC}\n"
else
    echo -e "${RED}Error: Failed to activate virtual environment${NC}"
    exit 1
fi

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1

# Install dependencies
echo "Installing dependencies..."
if pip install -r requirements.txt > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Dependencies installed${NC}\n"
else
    echo -e "${RED}Error: Failed to install dependencies${NC}"
    exit 1
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file not found${NC}"
    echo "A .env file is required to run this application."
    echo ""

    if [ -f ".env.example" ]; then
        read -p "Would you like to create .env from .env.example? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp .env.example .env
            echo -e "${GREEN}✓ Created .env file${NC}"
            echo -e "${YELLOW}Please edit .env and add your API keys:${NC}"
            echo "  - MERAKI_API_KEY"
            echo "  - ORGANIZATION_ID"
            echo "  - SNIPE_IT_API_KEY"
            echo "  - SNIPE_IT_URL"
        else
            echo -e "${YELLOW}Please create a .env file manually using .env.example as a template${NC}"
        fi
    fi
    echo ""
else
    echo -e "${GREEN}✓ .env file found${NC}\n"
fi

# Display completion message
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Activate the virtual environment (if not already active):"
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
echo "For more information, see README.md"
