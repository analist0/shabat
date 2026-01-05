# QWEN.md - Project Context for Voiseege (Shabbat-Safe Audio Intelligence System)

## Overview

This is the Voiseege project - an always-on, Shabbat-safe audio intelligence system designed to run locally on Android (Samsung Galaxy S24 Ultra) using Termux. The system operates with zero root access, zero cloud dependency, and strict Shabbat (Sabbath) compliance.

The system is designed to continuously record audio during Shabbat without any semantic processing, and then perform analysis, transcription, and data extraction after Shabbat ends.

## Project Architecture

The system is divided into three distinct phases:

### Phase 1 - Shabbat Mode (Passive Recorder)
- Continuous audio recording in small chunks (15-45s adaptive)
- Store Opus files with timestamps only
- No semantic database writes
- No deletion, dynamic notifications, or CPU upscaling
- Must comply with strict Shabbat rules

### Phase 2 - Post-Shabbat Processing
- VAD-based segmentation
- Whisper.cpp transcription (max 120s chunks)
- Detection of Torah Aliyah sales events
- Extraction of buyer name, Aliyah type, amount, and timestamp
- Attach exact audio proof clip to each sale

### Phase 3 - Dashboard (Human-in-the-Loop)
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

## Required Database Schema

The system must implement schemas for:
- raw_audio
- transcripts
- aliyah_sales
- congregants
- verification_log

Each Aliyah sale record must link to audio file, transcript, verification state, and human verifier (if any).

## Resilience & Recovery Requirements

The system must implement:
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

Detection must be rule-based first, LLM second:
- Speech length threshold
- Hebrew keyword patterns (e.g. "נמכר", "עולה", "שלוש מאות")
- Contextual proximity (name + amount)
- Confidence scoring
- LLM is allowed only as a verifier, never as the primary extractor

## Output Requirements

The final system must include:
- Full directory structure
- All runnable scripts
- Supervisor + workers
- Shabbat mode toggle
- Post-Shabbat pipeline
- Dashboard backend (API)
- Dashboard frontend (minimal, functional)
- Clear documentation

## Quality Standards

- Production-grade code
- Clear comments
- No placeholders
- No "TODO"
- No cloud assumptions
- No missing steps
- Everything must work offline
- Zero data loss tolerance

## Project Goal

This system serves as a complete, reliable, and halachically compliant solution for recording and tracking Aliyah sales during Shabbat services. It runs silently during Shabbat, accurately reconstructs Aliyah sales afterward, builds a trustworthy congregation database, provides audio-backed verification, and is defensible both halachically and technically.

This is not just software but a system of record for a community.