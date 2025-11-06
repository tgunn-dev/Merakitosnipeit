.PHONY: setup install run clean help activate

VENV_DIR := venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

help:
	@echo "Meraki to Snipe-IT Sync - Available Commands"
	@echo ""
	@echo "  make setup     Create virtual environment and install dependencies"
	@echo "  make install   Install/update dependencies (requires venv already created)"
	@echo "  make run       Run the sync (requires .env file configured)"
	@echo "  make activate  Print command to activate virtual environment"
	@echo "  make clean     Remove virtual environment and cached files"
	@echo "  make help      Show this help message"
	@echo ""

setup: $(VENV_DIR)
	@echo "Installing dependencies..."
	@$(PIP) install --upgrade pip setuptools wheel > /dev/null
	@$(PIP) install -r requirements.txt
	@echo ""
	@echo "Setup complete!"
	@echo ""
	@[ -f .env ] && echo "✓ .env file found" || echo "⚠ .env file not found - please create one from .env.example"
	@echo ""
	@echo "Activate with: source venv/bin/activate"
	@echo "Run with: python main.py"

$(VENV_DIR):
	@echo "Creating virtual environment..."
	@python3 -m venv $(VENV_DIR)
	@echo "✓ Virtual environment created"

install: $(VENV_DIR)
	@echo "Installing dependencies..."
	@$(PIP) install --upgrade pip setuptools wheel > /dev/null
	@$(PIP) install -r requirements.txt
	@echo "✓ Dependencies installed"

run: $(VENV_DIR)
	@[ -f .env ] || (echo "Error: .env file not found"; exit 1)
	@$(PYTHON) main.py

activate:
	@echo "Activate virtual environment with:"
	@echo "  source venv/bin/activate"

clean:
	@echo "Removing virtual environment and cache files..."
	@rm -rf $(VENV_DIR)
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cleaned up"
