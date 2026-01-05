#!/bin/bash
# Voiseege Startup Script
# Starts the Voiseege Shabbat-safe audio intelligence system

set -e  # Exit on any error

echo "==========================================="
echo "Voiseege Startup Script"
echo "Shabbat-Safe Audio Intelligence System"
echo "==========================================="

# Check if we're in the right directory
if [ ! -f "config.json" ]; then
    echo "Error: config.json not found. Please run this script from the voiseege directory."
    exit 1
fi

# Ensure required directories exist
mkdir -p audio db logs models

# Start the supervisor process
echo "Starting Voiseege Supervisor..."
python src/supervisor.py &

SUPERVISOR_PID=$!
echo "Supervisor started with PID: $SUPERVISOR_PID"

# Save the PID for potential later use
echo $SUPERVISOR_PID > supervisor.pid

# Set up wake lock to keep the device awake
echo "Acquiring wake lock..."
termux-wake-lock

echo "==========================================="
echo "Voiseege system started successfully!"
echo "Supervisor PID: $SUPERVISOR_PID"
echo ""
echo "To monitor the system:"
echo "  tail -f logs/supervisor.log"
echo "  tail -f logs/recorder.log"
echo "  tail -f logs/processing_pipeline.log"
echo ""
echo "To stop the system, run:"
echo "  ./scripts/stop.sh"
echo "==========================================="

# Wait for the supervisor process
wait $SUPERVISOR_PID