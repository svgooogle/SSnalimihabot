#!/usr/bin/env bash
# Exit on error
set -o errexit

# Create a virtual environment with Python 3.11.9
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
