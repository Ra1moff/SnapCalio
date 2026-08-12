#!/bin/bash

# Exit on any error
set -e

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=== SnapCal Bot Setup ==="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Check if Gemini key is present in .env
GEMINI_KEY=$(grep -E "^GEMINI_API_KEY=" .env | cut -d'=' -f2-)
if [ -z "$GEMINI_KEY" ] || [ "$GEMINI_KEY" == "your_gemini_api_key_here" ]; then
    echo "WARNING: GEMINI_API_KEY is not configured in .env!"
    echo "Please edit the .env file and set GEMINI_API_KEY to your actual Gemini API key before running."
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing/updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Running Bot ==="
python3 -u bot.py
