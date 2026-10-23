#!/usr/bin/env bash
cd "$(dirname "$0")"

echo "=========================================="
echo "  GeodeSync v1.1.2 (Linux / Steam Deck) ⚡"
echo "=========================================="

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required to run GeodeSync."
    echo "Please install python3 using your distribution's package manager (e.g. sudo apt install python3 python3-tk)."
    exit 1
fi

python3 main.py
