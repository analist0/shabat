#!/bin/bash

# Voiseege Live Log Script
# Shows live logs from the Voiseege system

echo "Starting Voiseege live log viewer..."
echo "Press Ctrl+C to exit"
echo ""

# Check if the log directory exists
if [ ! -d "./logs" ]; then
    echo "Error: logs directory not found!"
    exit 1
fi

# Check if any log files exist
if [ -z "$(ls -A ./logs 2>/dev/null)" ]; then
    echo "No log files found in ./logs directory."
    echo "Starting log viewer anyway (waiting for logs to appear)..."
fi

# Show logs from all log files with colors
echo "Showing logs from all components:"
echo "- RED: Errors"
echo "- YELLOW: Warnings" 
echo "- GREEN: Info messages"
echo "- BLUE: Debug messages"
echo ""

# Use multitail if available, otherwise use a custom solution
if command -v multitail &> /dev/null; then
    multitail ./logs/*.log
else
    # Fallback: use tail -f with colorization
    tail -f ./logs/*.log 2>/dev/null | \
    sed -e 's/.*ERROR.*/\x1b[31m&\x1b[0m/' \
        -e 's/.*WARNING.*/\x1b[33m&\x1b[0m/' \
        -e 's/.*INFO.*/\x1b[32m&\x1b[0m/' \
        -e 's/.*DEBUG.*/\x1b[34m&\x1b[0m/'
fi