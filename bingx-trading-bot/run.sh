#!/bin/bash
# Trading Engine Startup Script

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run with unbuffered output (-u) for real-time logs
python -u main.py
