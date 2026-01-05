#!/bin/bash

# Voiseege System Start Script
# Starts all components of the Voiseege system

echo "Starting Voiseege system..."

# Change to the project directory
cd "$(dirname "$0")/.." || exit 1

# Check if the system is already running
if pgrep -f "src/supervisor.py" > /dev/null; then
    echo "Voiseege system is already running!"
    echo "To restart, first run: ./scripts/stop.sh"
    exit 1
fi

# Start the supervisor (which manages all other components)
echo "Starting supervisor..."
python src/supervisor.py &

SUPERVISOR_PID=$!
echo "Supervisor started with PID: $SUPERVISOR_PID"

# Wait a moment for processes to start
sleep 3

# Verify that the main processes are running
if pgrep -f "src/supervisor.py" > /dev/null && \
   pgrep -f "src/recorder/recorder.py" > /dev/null && \
   pgrep -f "src/dashboard/server.py" > /dev/null; then
    echo "Voiseege system started successfully!"
    echo "Supervisor PID: $SUPERVISOR_PID"
    echo ""
    echo "System components:"
    echo "- Supervisor: Manages all processes"
    echo "- Recorder: Records audio in compliance with Shabbat rules"
    echo "- Processor: Handles post-Shabbat processing (VAD, transcription, detection)"
    echo "- Dashboard: Provides API for human review interface"
    echo ""
    echo "To view logs, run: ./scripts/live_log.sh"
    echo "To stop the system, run: ./scripts/stop.sh"
else
    echo "Error: Some components failed to start!"
    exit 1
fi