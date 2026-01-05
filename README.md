# Voiseege - Shabbat-Safe Audio Intelligence System

Voiseege is an always-on, Shabbat-safe audio intelligence system designed to run locally on Android devices using Termux. The system operates with zero root access, zero cloud dependency, and strict Shabbat compliance.

## Overview

The system is designed to continuously record audio during Shabbat without any semantic processing, and then perform analysis, transcription, and data extraction after Shabbat ends.

### System Architecture

The system is divided into three distinct phases:

#### Phase 1 - Shabbat Mode (Passive Recorder)
- Continuous audio recording in small chunks (15-45s adaptive)
- Store Opus files with timestamps only
- No semantic database writes
- No deletion, dynamic notifications, or CPU upscaling
- Must comply with strict Shabbat rules

#### Phase 2 - Post-Shabbat Processing
- VAD-based segmentation
- Whisper.cpp transcription (max 120s chunks)
- Detection of Torah Aliyah sales events
- Extraction of buyer name, Aliyah type, amount, and timestamp
- Attach exact audio proof clip to each sale

#### Phase 3 - Dashboard (Human-in-the-Loop)
- CRUD system for Aliyah sales and congregants
- Audio playback functionality
- Transcript display
- Verification system with confidence scoring
- Human review for low-confidence extractions

## Technical Stack

### Audio & ML Stack
- Audio capture: termux-microphone-record
- Audio codec: Opus (low bitrate, stable)
- VAD: Silero VAD via ONNX Runtime
- STT: whisper.cpp (compiled locally, ARM64)
- LLM: Local LLM (post-processing only, never during Shabbat)
- Database: SQLite with WAL + atomic write patterns

### Hardware & Environment
- Device: Samsung Galaxy S24 Ultra
- CPU: Snapdragon 8 Gen 3 (ARM64)
- OS: Android 14
- Environment: Termux
- Root: Not allowed
- NDK App: Not allowed
- GUI during runtime: Not allowed

## Shabbat Compliance Rules

### During Shabbat (Absolute Prohibitions):
- ❌ NOT write semantic data (names, money, purchases)
- ❌ NOT classify, infer, tag, or analyze content
- ❌ NOT invoke any LLM
- ❌ NOT allow user interaction
- ❌ NOT modify structured records

### During Shabbat (Permitted Actions):
- ✅ Record raw audio automatically
- ✅ Store audio files with timestamps only
- ✅ Run pre-started processes without interaction

All analysis, segmentation, transcription, extraction, and database writing must occur only AFTER Shabbat.

## Database Schema

The system implements schemas for:
- raw_audio
- transcripts
- aliyah_sales
- congregants
- verification_log

Each Aliyah sale record links to audio file, transcript, verification state, and human verifier (if any).

## Resilience & Recovery

The system implements:
- Supervisor process (never dies)
- Worker isolation (recorder / transcriber / watchdog)
- Memory leak fence (forced restart after N files)
- IO backpressure (token bucket)
- Thermal hard fence (pause above 48°C)
- SQLite WAL + double-write (pending.json)
- File system integrity repair on boot
- Termux wake-lock + foreground notification
- Ultimate keeper loop (restarts supervisor if killed)
- Termux-Boot auto-start after reboot
- Data loss tolerance: ZERO

## Aliyah Sale Detection Logic

Detection is rule-based first, LLM second:
- Speech length threshold
- Hebrew keyword patterns (e.g. "נמכר", "עולה", "שלוש מאות")
- Contextual proximity (name + amount)
- Confidence scoring
- LLM is allowed only as a verifier, never as the primary extractor

## Installation & Setup

1. Ensure Termux is installed on your Android device
2. Install required packages:
   ```bash
   pkg update && pkg upgrade
   pkg install python nodejs git
   pip install -r requirements.txt
   ```
3. Install termux-api for microphone access:
   ```bash
   pkg install termux-api
   ```
4. Install whisper.cpp for transcription (optional, for post-Shabbat processing)
5. Configure your Shabbat schedule in `config.json`

## Running the System

Start the system with:
```bash
python src/supervisor.py
```

The supervisor will start all necessary components:
- Audio recorder
- Post-Shabbat processor
- Dashboard API

## Repository Structure

```
voiseege/
├── config.json          # System configuration
├── requirements.txt     # Python dependencies
├── audio/              # Audio recordings
├── db/                 # SQLite database
├── logs/               # System logs
├── models/             # ML models (whisper, etc.)
├── scripts/            # Utility scripts
├── src/                # Source code
│   ├── dashboard/      # Dashboard API
│   ├── detector/       # Aliyah sale detection
│   ├── processor/      # Audio processing pipeline
│   ├── recorder/       # Audio recording
│   ├── database.py     # Database management
│   ├── shabbat_manager.py # Shabbat compliance
│   └── supervisor.py   # Main supervisor
└── tests/              # Test suite
```

## Shabbat Compliance Verification

This system has been designed and verified to comply with Shabbat laws:
- No semantic processing during Shabbat
- No user interaction during Shabbat
- No data modification during Shabbat
- All analysis deferred to post-Shabbat

## Contributing

Contributions are welcome! Please ensure any changes maintain Shabbat compliance and follow the architectural principles outlined in the documentation.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the repository or contact the maintainers.