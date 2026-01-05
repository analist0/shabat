#!/bin/bash

# Voiseege System Stop Script
# Stops all components of the Voiseege system

echo "Stopping Voiseege system..."

# Change to the project directory
cd "$(dirname "$0")/.." || exit 1

# Kill the supervisor process (which should stop all child processes)
SUPERVISOR_PIDS=$(pgrep -f "src/supervisor.py")

if [ -z "$SUPERVISOR_PIDS" ]; then
    echo "Voiseege system is not running!"
    exit 0
fi

echo "Found supervisor processes: $SUPERVISOR_PIDS"

# Kill the supervisor process (it should handle cleanup of child processes)
kill $SUPERVISOR_PIDS

# Wait a moment for processes to terminate
sleep 2

# Check if processes are still running and force kill if necessary
if pgrep -f "src/supervisor.py" > /dev/null; then
    echo "Supervisor still running, force killing..."
    pkill -9 -f "src/supervisor.py"
fi

if pgrep -f "src/recorder/recorder.py" > /dev/null; then
    echo "Recorder still running, force killing..."
    pkill -9 -f "src/recorder/recorder.py"
fi

if pgrep -f "src/processor/processor.py" > /dev/null; then
    echo "Processor still running, force killing..."
    pkill -9 -f "src/processor/processor.py"
fi

if pgrep -f "src/dashboard/server.py" > /dev/null; then
    echo "Dashboard still running, force killing..."
    pkill -9 -f "src/dashboard/server.py"
fi

# Stop any ongoing audio recording
if command -v termux-microphone-record &> /dev/null; then
    termux-microphone-record -q 2>/dev/null || true
fi

echo "Voiseege system stopped."