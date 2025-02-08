
#!/bin/bash

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed"
    exit 1
fi

# Install dependencies if not already installed
pip install -r requirements.txt

# Start the bot
python3 app.py
