#!/usr/bin/env python3
"""
Voiseege Audio Recorder - Records audio in compliance with Shabbat rules
Records raw audio during Shabbat but does not perform any semantic processing
"""

import os
import json
import time
import signal
import subprocess
import threading
import logging
from datetime import datetime
from pathlib import Path

# Import the database module
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import DatabaseManager
from shabbat_manager import ShabbatManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/recorder.log'),
        logging.StreamHandler()
    ]
)

class AudioRecorder:
    def __init__(self, config_path="../../config.json"):
        # Adjust the config path to be relative to the project root
        import os
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
        self.load_config()

        # Initialize database and Shabbat manager
        self.db = DatabaseManager(self.config['database']['path'])
        self.shabbat_manager = ShabbatManager()  # ShabbatManager now handles its own path resolution

        # State management
        self.running = True
        self.is_shabbat = False
        self.current_recording = None

        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        logging.info("Audio Recorder initialized")

    def load_config(self):
        """Load configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        logging.info(f"Configuration loaded from {self.config_path}")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logging.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False

    def generate_filename(self):
        """Generate a filename for the audio recording"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audio_{timestamp}.opus"
        filepath = os.path.join(self.config['paths']['audio_dir'], filename)
        return filepath

    def record_audio_chunk(self, duration):
        """Record a single audio chunk using termux-microphone-record"""
        filepath = self.generate_filename()

        try:
            # Use termux-microphone-record to capture audio
            # Format: termux-microphone-record -f filepath -l duration -e opus -b bitrate -r sample_rate
            cmd = [
                "termux-microphone-record",
                "-f", filepath,
                "-l", str(duration),  # Duration in seconds
                "-e", self.config['audio']['codec'],
                "-b", str(self.config['audio']['bitrate']),
                "-r", str(self.config['audio']['sample_rate'])
            ]

            logging.info(f"Starting audio recording: {filepath} with command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 5)

            if result.returncode == 0:
                # Verify that the file was actually created
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    logging.info(f"Successfully recorded: {filepath}")

                    # Check Shabbat status at the time of recording
                    is_shabbat_now = self.shabbat_manager.is_currently_shabbat()

                    # Store in database (only metadata during Shabbat, as per requirements)
                    recording_start = datetime.now().isoformat()
                    filename = os.path.basename(filepath)

                    # Insert into database
                    audio_id = self.db.insert_raw_audio(
                        filename=filename,
                        filepath=filepath,
                        recording_start=recording_start,
                        duration=duration,
                        shabbat_mode=is_shabbat_now
                    )

                    logging.info(f"Audio record inserted into DB with ID: {audio_id}")

                    # Create a metadata file with timestamp only (no semantic data during Shabbat)
                    metadata_path = filepath.replace('.opus', '.json')
                    metadata = {
                        "id": audio_id,
                        "recording_start": recording_start,
                        "duration": duration,
                        "filename": filename,
                        "shabbat_mode": is_shabbat_now
                    }

                    with open(metadata_path, 'w') as f:
                        json.dump(metadata, f, indent=2)

                    logging.info(f"Metadata saved: {metadata_path}")
                    return filepath, audio_id
                else:
                    logging.error(f"Recording command succeeded but file was not created or is empty: {filepath}")
                    return None, None
            else:
                logging.error(f"Recording failed: {result.stderr}")
                return None, None

        except subprocess.TimeoutExpired:
            logging.error(f"Recording timed out for {filepath}")
            # Stop any ongoing recording
            try:
                subprocess.run(["termux-microphone-record", "-q"], capture_output=True, text=True)
            except:
                pass  # Ignore errors when stopping
            return None, None
        except Exception as e:
            logging.error(f"Error during recording: {e}")
            # Stop any ongoing recording
            try:
                subprocess.run(["termux-microphone-record", "-q"], capture_output=True, text=True)
            except:
                pass  # Ignore errors when stopping
            return None, None

    def run(self):
        """Main recording loop"""
        logging.info("Starting Audio Recorder...")

        while self.running:
            # Check if it's currently Shabbat
            self.is_shabbat = self.shabbat_manager.is_currently_shabbat()

            # Determine recording duration based on mode
            if self.is_shabbat:
                duration = self.config['audio']['chunk_duration']
                logging.info("Shabbat mode active - recording audio only, no semantic processing")
            else:
                # During non-Shabbat, we can still record but may process differently
                duration = self.config['audio']['chunk_duration']
                logging.info("Non-Shabbat mode - recording audio")

            # Record a chunk
            recording_path, audio_id = self.record_audio_chunk(duration)

            if recording_path is None:
                logging.error("Recording failed, waiting before retry...")
                time.sleep(5)
                continue

            # Small delay between recordings
            time.sleep(1)

        logging.info("Audio Recorder shutdown complete")

        # Close database connection
        self.db.close()


if __name__ == "__main__":
    recorder = AudioRecorder()
    recorder.run()