#!/bin/bash
# Voiseege Complete Setup Script - Updated for ONNX Runtime
# Sets up the Voiseege Shabbat-safe audio intelligence system

set -e  # Exit on any error

echo "==========================================="
echo "Voiseege Complete Setup Script"
echo "Shabbat-Safe Audio Intelligence System"
echo "==========================================="

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Check if running on Termux
if [ -n "$TERMUX_VERSION" ]; then
    echo "✓ Detected Termux environment"
    IS_TERMUX=1
else
    echo "⚠ Not running in Termux - some features may not work on Android"
    IS_TERMUX=0
fi

# Update package list
echo ""
echo "1. Updating package list..."
if [ $IS_TERMUX -eq 1 ]; then
    pkg update
else
    echo "  Skipping package update (not in Termux)"
fi

# Install required system packages
echo ""
echo "2. Installing required system packages..."
if [ $IS_TERMUX -eq 1 ]; then
    pkg install -y python git ffmpeg sox wget cmake make clang
else
    echo "  Please install: python3 git ffmpeg sox wget cmake make g++"
fi

# Install Python dependencies
echo ""
echo "3. Installing Python dependencies..."
pip install --upgrade pip
pip install pytz psutil flask flask-cors onnxruntime numpy scipy

echo "✓ Python packages installed"

# Initialize whisper.cpp submodule
echo ""
echo "4. Initializing whisper.cpp submodule..."
git submodule update --init --recursive
echo "✓ Whisper.cpp submodule initialized"

# Compile whisper.cpp
echo ""
echo "5. Compiling whisper.cpp..."
cd whisper.cpp

if [ -d "build" ]; then
    echo "  Cleaning previous build..."
    rm -rf build
fi

make -j4
echo "✓ Whisper.cpp compiled successfully"

cd "$PROJECT_ROOT"

# Download Whisper model if not exists
echo ""
echo "6. Checking Whisper model..."
WHISPER_MODEL="$PROJECT_ROOT/models/ggml-medium.bin"

if [ -f "$WHISPER_MODEL" ]; then
    echo "✓ Whisper model already exists"
else
    echo "  Downloading Whisper Medium model (1.5GB)..."
    echo "  This may take several minutes..."
    mkdir -p models
    wget -O "$WHISPER_MODEL" \
        https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin
    echo "✓ Whisper model downloaded"
fi

# Download Silero VAD ONNX model
echo ""
echo "7. Checking Silero VAD ONNX model..."
VAD_MODEL="$PROJECT_ROOT/models/silero_vad.onnx"

if [ -f "$VAD_MODEL" ]; then
    echo "✓ Silero VAD model already exists"
else
    echo "  Downloading Silero VAD ONNX model..."
    wget -O "$VAD_MODEL" \
        https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx
    echo "✓ Silero VAD model downloaded"
fi

# Create necessary directories
echo ""
echo "8. Creating directory structure..."
mkdir -p audio audio/segments audio/sales
mkdir -p db
mkdir -p logs
mkdir -p models

echo "✓ Directories created"

# Initialize database
echo ""
echo "9. Initializing database..."
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/src')
from database import DatabaseManager
db = DatabaseManager('$PROJECT_ROOT/db/voiseege.db')
print('✓ Database initialized')
db.close()
"

# Make scripts executable
echo ""
echo "10. Setting permissions..."
chmod +x "$PROJECT_ROOT/scripts/"*.sh
chmod +x "$PROJECT_ROOT/src/supervisor.py"
chmod +x "$PROJECT_ROOT/src/recorder/recorder.py"
chmod +x "$PROJECT_ROOT/src/processor/processor.py"
chmod +x "$PROJECT_ROOT/src/detector/detector.py"
chmod +x "$PROJECT_ROOT/src/dashboard/server.py"

echo "✓ Permissions set"

# Setup Termux services (if in Termux)
if [ $IS_TERMUX -eq 1 ]; then
    echo ""
    echo "11. Setting up Termux services..."

    if [ ! -d "$HOME/.termux-services" ]; then
        mkdir -p "$HOME/.termux-services"
    fi

    # Create service script
    cat > "$HOME/.termux-services/voiseege" << EOF
#!/bin/bash
cd $PROJECT_ROOT
python3 src/supervisor.py
EOF

    chmod +x "$HOME/.termux-services/voiseege"
    echo "✓ Termux service configured"
fi

# Summary
echo ""
echo "==========================================="
echo "✓ Installation completed successfully!"
echo "==========================================="
echo ""
echo "System Information:"
echo "  - Project Root: $PROJECT_ROOT"
echo "  - Whisper Model: $(du -h "$WHISPER_MODEL" | cut -f1)"
echo "  - Database: $PROJECT_ROOT/db/voiseege.db"
echo ""
echo "To start the system:"
echo "  ./scripts/start.sh"
echo ""
echo "To stop the system:"
echo "  ./scripts/stop.sh"
echo ""
echo "To view live logs:"
echo "  ./scripts/live_log.sh"
echo ""

if [ $IS_TERMUX -eq 1 ]; then
    echo "Termux service commands:"
    echo "  termux-services enable voiseege"
    echo "  termux-services start voiseege"
    echo "  termux-services status voiseege"
    echo "  termux-services stop voiseege"
    echo ""
fi

echo "For more information, see README.md and CLAUDE.md"
echo "==========================================="
