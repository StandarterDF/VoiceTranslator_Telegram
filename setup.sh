#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo ""
echo "======================================"
echo "  VoiceTranslator - Setup"
echo "======================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 is not found in PATH. Please install Python 3.10+."
    exit 1
fi
echo "[1/3] Python found:"
python3 --version
echo ""

# Create virtual environment if not exists
if [ ! -f ./venv/bin/python3 ]; then
    echo "[2/3] Creating virtual environment..."
    python3 -m venv ./venv
    echo "Virtual environment created."
else
    echo "[2/3] Virtual environment already exists, skipping creation."
fi
echo ""

# Install dependencies
echo "[3/3] Upgrading pip and installing dependencies..."
./venv/bin/pip install --upgrade pip > /dev/null 2>&1 || echo "[WARNING] pip upgrade failed, continuing anyway."
./venv/bin/pip install -r ./requirements.txt
echo "Dependencies installed."
echo ""

# Copy .env.example to .env if .env does not exist
if [ ! -f ./.env ]; then
    echo "Copying .env.example to .env (you need to edit it with your BOT_TOKEN)."
    cp .env.example .env
    echo ""
else
    echo ".env already exists, skipping."
    echo ""
fi

echo "======================================"
echo "  Setup complete!"
echo "  Edit .env with your BOT_TOKEN,"
echo "  then run: ./venv/bin/python tui_app.py"
echo "  or: ./venv/bin/python run.py --provider faster_whisper --size small"
echo "======================================"
