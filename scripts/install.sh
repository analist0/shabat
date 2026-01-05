#!/bin/bash
# Voiseege Installation Script
# Sets up the Voiseege Shabbat-safe audio intelligence system

set -e  # Exit on any error

echo "==========================================="
echo "Voiseege Installation Script"
echo "Shabbat-Safe Audio Intelligence System"
echo "==========================================="

# Check if running on Termux
if [ -z "$TERMUX_VERSION" ]; then
    echo "Error: This script must be run in Termux on Android"
    exit 1
fi

# Update package list
echo "Updating package list..."
pkg update

# Install required packages
echo "Installing required packages..."
pkg install -y python nodejs ffmpeg sox

# Install Python dependencies
echo "Installing Python dependencies..."
pip install pytz psutil flask flask-cors

# Install PyTorch and torchaudio (these may need special handling in Termux)
echo "Installing PyTorch and torchaudio (this may take a while)..."
# Check if we're in Termux and handle PyTorch installation appropriately
if [ -n "$TERMUX_VERSION" ]; then
    # For Termux, PyTorch may not be available for ARM64, so we'll handle this gracefully
    echo "Detected Termux environment, attempting to install PyTorch for ARM64..."
    if pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu; then
        echo "PyTorch installed successfully"
    else
        echo "PyTorch installation failed. This is common in Termux on ARM64."
        echo "You may need to build PyTorch from source or use an alternative approach."
        echo "See documentation for more details."
        # Continue with installation anyway
    fi
else
    pip install torch torchaudio
fi

# Install whisper.cpp
echo "Installing whisper.cpp..."
if [ ! -d "whisper.cpp" ]; then
    git clone https://github.com/ggerganov/whisper.cpp.git
    cd whisper.cpp
    make
    cd ..
else
    echo "whisper.cpp already exists, skipping clone"
fi

# Install Silero VAD model
echo "Installing Silero VAD model..."
if python -c "import torch; torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False)" 2>/dev/null; then
    echo "Silero VAD model installed successfully"
else
    echo "Silero VAD model installation failed (expected if PyTorch is not available)"
    echo "The system will use fallback methods when PyTorch is not available"
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p audio db logs scripts models

# Download a Whisper model (medium-sized, good balance of accuracy and size)
echo "Downloading Whisper model..."
if [ ! -f "models/ggml-medium.bin" ]; then
    wget -O models/ggml-medium.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin
else
    echo "Whisper model already exists, skipping download"
fi

# Make scripts executable
echo "Setting permissions..."
chmod +x src/supervisor.py
chmod +x src/recorder/recorder.py
chmod +x src/processor/processor.py
chmod +x src/detector/detector.py
chmod +x src/dashboard/server.py

# Setup Termux services
echo "Setting up Termux services..."
if [ ! -d "$HOME/.termux-services" ]; then
    mkdir -p $HOME/.termux-services
fi

# Create service script
cat > $HOME/.termux-services/voiseege << 'EOF'
#!/bin/bash
cd $HOME/voiseege
python src/supervisor.py
EOF

chmod +x $HOME/.termux-services/voiseege

echo "==========================================="
echo "Installation completed!"
echo ""
echo "To start the system, run:"
echo "  termux-services enable voiseege"
echo "  termux-services start voiseege"
echo ""
echo "To check the status:"
echo "  termux-services status voiseege"
echo ""
echo "To stop the system:"
echo "  termux-services stop voiseege"
echo "==========================================="