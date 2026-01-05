# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Voiseege is a Shabbat-safe audio intelligence system that records audio during Shabbat without semantic processing, then performs transcription and aliyah sale detection after Shabbat ends. The system runs locally on Android devices using Termux with zero root access and zero cloud dependency.

## Critical Shabbat Compliance Rules

**ABSOLUTE PROHIBITIONS during Shabbat:**
- Never write semantic data (names, money amounts, classifications)
- Never invoke LLMs or perform analysis/inference
- Never modify structured records beyond timestamps
- Never allow user interaction

**Permitted during Shabbat:**
- Record raw audio automatically
- Store audio files with timestamps only
- Run pre-started processes without interaction

The `ShabbatManager` class (src/shabbat_manager.py) controls compliance. Always check `shabbat_manager.is_currently_shabbat()` before any semantic operation. Violating Shabbat rules is unacceptable.

## System Architecture

### Three-Phase Pipeline

1. **Phase 1 - Shabbat Mode (Recording)**
   - Continuous audio recording in 15-45s chunks
   - Store Opus files with timestamps only
   - No semantic database writes
   - Managed by `src/recorder/recorder.py`

2. **Phase 2 - Post-Shabbat Processing**
   - VAD-based segmentation (`src/processor/vad_segmenter.py`)
   - Whisper.cpp transcription (`src/processor/whisper_transcriber.py`)
   - Aliyah sale detection (`src/detector/detector.py`)
   - Coordinated by `src/processor/processor.py`

3. **Phase 3 - Dashboard**
   - Human-in-the-loop verification
   - CRUD for aliyah sales and congregants
   - Audio playback and transcript review
   - Served by `src/dashboard/server.py`

### Process Management

The `src/supervisor.py` manages all components:
- Monitors child processes and restarts on failure
- Enforces thermal limits (48°C hard fence)
- Implements memory leak fence (restart after N files)
- Provides IO backpressure via token bucket
- Uses SQLite WAL mode + atomic writes

### Database Schema

SQLite database at `./db/voiseege.db` with WAL mode enabled:
- `raw_audio`: Audio recordings with timestamps and Shabbat mode flag
- `transcripts`: Whisper transcriptions linked to audio_id
- `aliyah_sales`: Detected sales with confidence scores
- `congregants`: Buyer information
- `verification_log`: Human verification audit trail

Database manager in `src/database.py` handles all DB operations.

## Development Commands

### System Management

```bash
# Start the entire system (supervisor + all components)
./scripts/start.sh

# Stop all system processes
./scripts/stop.sh

# View live logs from all components
./scripts/live_log.sh

# Install dependencies and setup
./scripts/install.sh
```

### Running Individual Components

```bash
# Run supervisor directly
python src/supervisor.py

# Run recorder standalone (for testing)
python src/recorder/recorder.py

# Run post-Shabbat pipeline once
python src/processor/processor.py

# Run processor in continuous mode
python src/processor/processor.py --continuous

# Run dashboard API server
python src/dashboard/server.py

# Test VAD segmentation on an audio file
python src/processor/vad_segmenter.py <audio_file>

# Test detector on sample data
python src/detector/detector.py
```

### Environment Setup

This system is designed for Termux on Android:
```bash
pkg update && pkg upgrade
pkg install python nodejs git
pip install -r requirements.txt
pkg install termux-api  # Required for microphone access
```

Dependencies in `requirements.txt`:
- torch, torchaudio: Silero VAD model
- pytz: Timezone handling for Shabbat calculations
- psutil: System monitoring
- flask, flask-cors: Dashboard API

## Configuration

All configuration is in `config.json`:
- Audio settings: chunk duration, codec, sample rate, bitrate
- VAD parameters: threshold, silence/speech duration
- Whisper settings: model path, language, beam size
- Database: path and WAL settings
- Shabbat schedule: timezone, start/end hours
- System limits: max temperature, memory limit, restart threshold
- Paths: audio_dir, log_dir, model_dir

## File Path Resolution

Many modules use dynamic path resolution to find `config.json`:
- Modules in `src/` look for `../config.json`
- Modules in `src/recorder/` and `src/processor/` look for `../../config.json`
- The pattern is: `os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")`

When adding new modules, ensure they correctly resolve the project root to find config.json.

## Audio Processing Pipeline

1. **Recording** (`recorder.py`):
   - Uses `termux-microphone-record` command
   - Records to `./audio/audio_YYYYMMDD_HHMMSS.opus`
   - Creates metadata JSON with timestamp only during Shabbat
   - Inserts into `raw_audio` table with `shabbat_mode` flag

2. **Segmentation** (`vad_segmenter.py`):
   - Uses Silero VAD via PyTorch (with fallback if unavailable)
   - Detects speech segments from raw audio
   - Returns list of (start_time, end_time) tuples

3. **Transcription** (`whisper_transcriber.py`):
   - Uses whisper.cpp for Hebrew transcription
   - Processes audio files up to 120s chunks
   - Returns transcript with confidence scores

4. **Detection** (`detector.py`):
   - Rule-based detection of aliyah sales using Hebrew keywords
   - Extracts: buyer name, aliyah type, amount, timestamp
   - LLM verification is optional and only as secondary validator
   - Never use LLM as primary extractor

## Aliyah Sale Detection Logic

The detector (`src/detector/detector.py`) uses:
- Hebrew keyword patterns for sale indicators (נמכר, עולה, etc.)
- Monetary amount extraction (שקל, שקלים, NIS)
- Name extraction patterns (ben/בן patterns, Hebrew names)
- Aliyah type detection (torah, maftir, bridegroom)
- Confidence scoring based on elements present

Detection is rule-based first, never LLM-first. LLM should only verify, never extract.

## Logging

All components log to:
- `./logs/supervisor.log`: Supervisor process
- `./logs/recorder.log`: Audio recorder
- `./logs/processing_pipeline.log`: Post-Shabbat pipeline
- `./logs/vad.log`: VAD segmentation
- `./logs/detector.log`: Aliyah sale detection
- `./logs/database.log`: Database operations
- `./logs/shabbat.log`: Shabbat compliance checks

Log format: `%(asctime)s - %(levelname)s - %(message)s`

## Testing Approach

When testing or modifying code:
1. Always verify Shabbat compliance first
2. Test audio recording without actual termux commands (mock when needed)
3. Use sample audio files in `./audio/` for pipeline testing
4. Verify database operations don't violate WAL mode assumptions
5. Check that supervisor properly restarts failed components
6. Ensure thermal and memory limits are respected

## Key Architectural Constraints

1. **Environment**: Android/Termux, no root, no NDK apps
2. **Hardware**: Samsung Galaxy S24 Ultra (Snapdragon 8 Gen 3 ARM64)
3. **Resilience**: Zero data loss tolerance - use WAL + double-write patterns
4. **Thermal**: Hard fence at 48°C, pause operations above limit
5. **Memory**: Forced restart after memory_limit_mb or restart_after_files
6. **Shabbat**: Absolute compliance - semantic processing only post-Shabbat
7. **Audio**: Opus codec preferred for low bitrate and stability
8. **Transcription**: Hebrew language (language="he" in config)

## Common Workflows

### Adding a New Processing Step

1. Check if it's semantic processing → must respect Shabbat mode
2. Add to `processor.py` pipeline after Shabbat check
3. Update database schema if storing new data types
4. Add logging to appropriate log file
5. Update supervisor if it needs separate process management

### Modifying Shabbat Logic

1. Edit `shabbat_manager.py` calculation logic
2. Update config.json for timezone/hours if needed
3. Test with `python src/shabbat_manager.py` to verify
4. Never change the compliance rules - only the time calculations

### Database Schema Changes

1. Edit `database.py` CREATE TABLE statements
2. Add corresponding insert/query methods
3. Consider migration if database already exists
4. Test with WAL mode enabled
5. Verify foreign key constraints are maintained
