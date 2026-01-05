#!/bin/bash
# Voiseege Stop Script
# Stops the Voiseege Shabbat-safe audio intelligence system

set -e  # Exit on any error

echo "==========================================="
echo "Voiseege Stop Script"
echo "Shabbat-Safe Audio Intelligence System"
echo "==========================================="

# Check if supervisor PID file exists
if [ -f "supervisor.pid" ]; then
    SUPERVISOR_PID=$(cat supervisor.pid)
    
    if ps -p $SUPERVISOR_PID > /dev/null; then
        echo "Stopping supervisor process (PID: $SUPERVISOR_PID)..."
        kill $SUPERVISOR_PID
        
        # Wait a moment for graceful shutdown
        sleep 3
        
        # Check if process is still running
        if ps -p $SUPERVISOR_PID > /dev/null; then
            echo "Process still running, force killing..."
            kill -9 $SUPERVISOR_PID
        fi
        
        # Remove the PID file
        rm supervisor.pid
        echo "Supervisor process stopped."
    else
        echo "Supervisor process (PID: $SUPERVISOR_PID) not found."
        rm supervisor.pid
    fi
else
    echo "No supervisor PID file found. Looking for running processes..."
    
    # Try to find and kill any running voiseege processes
    PIDS=$(ps aux | grep "python src/supervisor.py" | grep -v grep | awk '{print $2}')
    
    if [ ! -z "$PIDS" ]; then
        echo "Found and stopping processes: $PIDS"
        kill $PIDS
        sleep 2
        
        # Force kill if still running
        PIDS=$(ps aux | grep "python src/supervisor.py" | grep -v grep | awk '{print $2}')
        if [ ! -z "$PIDS" ]; then
            kill -9 $PIDS
        fi
    else
        echo "No running Voiseege processes found."
    fi
fi

# Release wake lock
echo "Releasing wake lock..."
termux-wake-unlock

echo "==========================================="
echo "Voiseege system stopped."
echo "==========================================="