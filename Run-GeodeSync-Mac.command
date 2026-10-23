#!/usr/bin/env bash
cd "$(dirname "$0")"

echo "=========================================="
echo "       GeodeSync v1.1.2 for macOS ⚡"
echo "=========================================="

if ! command -v python3 &> /dev/null; then
    echo "Python 3 was not found on your Mac."
    echo "Opening official Python download page in your browser..."
    open "https://www.python.org/downloads/macos/"
    read -p "Press Enter to exit..."
    exit 1
fi

# Launch GeodeSync with Python 3
python3 main.py
