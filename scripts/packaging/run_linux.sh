#!/bin/bash
# Linux launcher script for Log Analysis & CTI Tool

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.7 or higher."
    echo "On Ubuntu/Debian: sudo apt install python3 python3-pip"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check for required system libraries
echo "Checking system dependencies..."
if ! dpkg -l | grep -q libgl1-mesa-glx; then
    echo "Warning: libgl1-mesa-glx not found. GUI may not work properly."
    echo "Install with: sudo apt install libgl1-mesa-glx libxcb-xinerama0"
fi

# Launch the application
echo "Launching Log Analysis & CTI Tool..."
python3 gui_app.py

# Deactivate virtual environment
deactivate
