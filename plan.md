🧠 MASTER PROMPT – Always-On Shabbat-Safe Audio Intelligence System
(להעתקה כפי שהוא ל-Claude Code)
🎯 ROLE & EXPECTATION
You are Claude Code acting as a Principal Systems Architect + Senior Embedded/Backend Engineer.
Your task is to design and implement a complete, production-grade, always-on audio intelligence system that runs locally on Android (Samsung Galaxy S24 Ultra) using Termux, with zero root, zero cloud dependency, and strict Shabbat (Sabbath) compliance.
This is not a demo.
This is a real system intended to run 24/7, survive crashes, heat, memory fragmentation, and Android process killing — and recover automatically.
You must output clean, production-ready code, structured documentation, and a runnable system.
🧩 HARD CONSTRAINTS (NON-NEGOTIABLE)
📱 Hardware & OS
Device: Samsung Galaxy S24 Ultra
CPU: Snapdragon 8 Gen 3 (ARM64)
OS: Android 14
Environment: Termux
Root: ❌ forbidden
NDK App: ❌ forbidden
GUI during runtime: ❌ forbidden
🧠 Audio & ML Stack (MUST USE)
Audio capture: termux-microphone-record
Audio codec: Opus (low bitrate, stable)
STT: whisper.cpp (compiled locally, ARM64)
VAD: Silero VAD via ONNX Runtime (NOT PyTorch runtime)
LLM (optional, post-processing only): Local LLM (never during Shabbat)
Database: SQLite with WAL + atomic write patterns
🕯️ HALACHIC (SHABBAT) RULES – ABSOLUTE
During Shabbat the system must:
❌ NOT write semantic data (names, money, purchases)
❌ NOT classify, infer, tag, or analyze content
❌ NOT invoke any LLM
❌ NOT allow user interaction
❌ NOT modify structured records
During Shabbat the system is allowed to:
✅ Record raw audio automatically
✅ Store audio files with timestamps only
✅ Run pre-started processes without interaction
All analysis, segmentation, transcription, extraction, and database writing must occur only AFTER Shabbat.
🧱 REQUIRED ARCHITECTURE
Design the system using strict separation of phases:
🕯️ Phase 1 – Shabbat Mode (Passive Recorder)
Continuous audio recording in small chunks (15–45s adaptive)
Store Opus files + timestamps only
No semantic DB writes
No deletion
No dynamic notifications
No CPU upscaling
🌙 Phase 2 – Post-Shabbat Processing
VAD-based segmentation
Whisper.cpp transcription (max 120s chunks)
Detection of Torah Aliyah sales events
Extraction of:
Buyer name
Aliyah type
Amount
Timestamp
Attach exact audio proof clip to each sale
🖥️ Phase 3 – Dashboard (Human-in-the-Loop)
CRUD system for:
Aliyah sales
Congregants (public members)
Each sale must include:
Audio playback button
Transcript
Machine-extracted fields
Confidence score
Verification button:
Plays audio
Runs local LLM verification (optional)
If confidence < threshold → flag for human review
🛡️ RESILIENCE & RECOVERY (MANDATORY)
Implement all of the following:
Supervisor process (never dies)
Worker isolation (recorder / transcriber / watchdog)
Memory leak fence (forced restart after N files)
IO backpressure (token bucket)
Thermal hard fence (pause above 48°C)
SQLite WAL + double-write (pending.json)
File system integrity repair on boot
Termux wake-lock + foreground notification
Ultimate keeper loop (restarts supervisor if killed)
Termux-Boot auto-start after reboot
Data loss tolerance: ZERO.
📊 REQUIRED DATABASE SCHEMA
You must design and implement schemas for:
raw_audio
transcripts
aliyah_sales
congregants
verification_log
Each Aliyah sale record MUST link to:
Audio file
Transcript
Verification state
Human verifier (if any)
🧠 ALIYAH SALE DETECTION LOGIC
Detection must be rule-based first, LLM second:
Speech length threshold
Hebrew keyword patterns (e.g. “נמכר”, “עולה”, “שלוש מאות”)
Contextual proximity (name + amount)
Confidence scoring
LLM is allowed only as a verifier, never as the primary extractor.
🎨 OUTPUT REQUIREMENTS
You must produce:
Full directory structure
All runnable scripts
Supervisor + workers
Shabbat mode toggle
Post-Shabbat pipeline
Dashboard backend (API)
Dashboard frontend (minimal, functional)
Clear documentation:
How to install
How to start
How to run before Shabbat
How verification works
What is allowed / forbidden during Shabbat
🧾 STYLE & QUALITY
Production-grade code
Clear comments
No placeholders
No “TODO”
No cloud assumptions
No missing steps
Everything must work offline
🏁 FINAL GOAL
The result should be a complete, beautiful, reliable system that:
Runs silently during Shabbat
Accurately reconstructs Aliyah sales afterward
Builds a trustworthy congregation database
Provides audio-backed verification
Is defensible halachically and technically
This is not just software.
This is a system of record for a community.
Begin by designing the architecture, then implement it fully.

