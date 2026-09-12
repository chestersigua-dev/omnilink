#!/usr/bin/env bash
set -e

echo "======================================================="
echo "  OmniLink Universal IoT Platform - Bootstrapper (POSIX)"
echo "======================================================="

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "[!] python3 not found. Attempting to install via package manager..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
    elif command -v brew &> /dev/null; then
        brew install python
    else
        echo "[X] Please install Python 3.10+ manually."
        exit 1
    fi
fi

# Setup virtual environment
if [ ! -d ".venv" ]; then
    echo "[*] Creating isolated virtual environment (.venv)..."
    python3 -m venv .venv
fi

# Activate virtualenv
source .venv/bin/activate

echo "[*] Installing project dependencies quietly..."
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

# Create storage directories
mkdir -p uploads/avatars static

echo "[*] Launching OmniLink Monolithic Server on http://0.0.0.0:8000..."
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
