#!/usr/bin/env python3
"""
Voiseege VAD (Voice Activity Detection) Module - Uses Silero VAD with ONNX Runtime
"""

import os
import json
import logging
import numpy as np
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/vad.log'),
        logging.StreamHandler()
    ]
)

class VADSegmenter:
    def __init__(self, config_path="../../config.json"):
        # Adjust the config path to be relative to the project root
        import os
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
        self.load_config()

        # Try to load ONNX Runtime and Silero VAD model
        self.onnx_available = self.check_onnx_availability()
        if self.onnx_available:
            self.load_vad_model()
        else:
            logging.warning("ONNX Runtime not available, VAD functionality will be limited")

        logging.info("VAD Segmenter initialized")

    def check_onnx_availability(self):
        """Check if ONNX Runtime is available"""
        try:
            import onnxruntime as ort
            import numpy as np
            return True
        except ImportError:
            return False

    def load_config(self):
        """Load configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        logging.info(f"Configuration loaded from {self.config_path}")

    def load_vad_model(self):
        """Load the Silero VAD ONNX model"""
        try:
            import onnxruntime as ort

            # Path to the ONNX model
            model_path = "./models/silero_vad.onnx"

            # Check if model exists, if not, download it
            if not os.path.exists(model_path):
                logging.info("Downloading Silero VAD ONNX model...")
                self.download_silero_vad_onnx()

            # Load the ONNX model
            self.ort_session = ort.InferenceSession(model_path)

            # Initialize state
            self.reset_states()

            logging.info("Silero VAD ONNX model loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load Silero VAD ONNX model: {e}")
            self.ort_session = None

    def download_silero_vad_onnx(self):
        """Download the Silero VAD ONNX model"""
        import urllib.request

        url = "https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx"
        model_path = "./models/silero_vad.onnx"

        os.makedirs("./models", exist_ok=True)

        try:
            urllib.request.urlretrieve(url, model_path)
            logging.info(f"Downloaded Silero VAD ONNX model to {model_path}")
        except Exception as e:
            logging.error(f"Failed to download Silero VAD ONNX model: {e}")
            raise

    def reset_states(self):
        """Reset the VAD model states"""
        self.h = np.zeros((2, 1, 64), dtype=np.float32)
        self.c = np.zeros((2, 1, 64), dtype=np.float32)

    def read_audio(self, path, target_sr=16000):
        """Read audio file and convert to the required format"""
        try:
            import subprocess
            import tempfile

            # Use ffmpeg to convert audio to 16kHz mono WAV
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp_path = tmp.name

            cmd = [
                'ffmpeg', '-i', path,
                '-ar', str(target_sr),
                '-ac', '1',
                '-f', 'wav',
                '-y', tmp_path
            ]

            subprocess.run(cmd, capture_output=True, check=True)

            # Read the WAV file
            import wave
            with wave.open(tmp_path, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

            # Clean up
            os.unlink(tmp_path)

            return audio, target_sr

        except Exception as e:
            logging.error(f"Error reading audio file {path}: {e}")
            return None, None

    def segment_audio(self, audio_path):
        """
        Segment audio file using VAD to identify speech segments
        Returns list of (start_time, end_time) tuples in seconds
        """
        if not self.onnx_available or self.ort_session is None:
            # Fallback implementation when ONNX is not available
            logging.warning("ONNX not available, using simplified segmentation")
            return self.simple_segmentation(audio_path)

        try:
            # Read the audio file
            audio, sr = self.read_audio(audio_path, target_sr=16000)

            if audio is None:
                return []

            # Reset states
            self.reset_states()

            # Process audio in chunks
            window_size_samples = 512  # 32ms at 16kHz
            threshold = self.config['vad']['threshold']
            min_silence_duration_samples = int(self.config['vad']['min_silence_duration'] * sr)
            min_speech_duration_samples = int(self.config['vad']['min_speech_duration'] * sr)

            speech_timestamps = []
            current_speech_start = None
            silence_start = None

            for i in range(0, len(audio), window_size_samples):
                chunk = audio[i:i + window_size_samples]

                if len(chunk) < window_size_samples:
                    # Pad the last chunk
                    chunk = np.pad(chunk, (0, window_size_samples - len(chunk)))

                # Run inference
                chunk = chunk.reshape(1, -1).astype(np.float32)
                ort_inputs = {
                    'input': chunk,
                    'h': self.h,
                    'c': self.c,
                    'sr': np.array([sr], dtype=np.int64)
                }

                ort_outs = self.ort_session.run(None, ort_inputs)
                speech_prob = ort_outs[0][0][0]
                self.h = ort_outs[1]
                self.c = ort_outs[2]

                # Update speech state
                if speech_prob >= threshold:
                    if current_speech_start is None:
                        current_speech_start = i
                    silence_start = None
                else:
                    if current_speech_start is not None:
                        if silence_start is None:
                            silence_start = i
                        elif (i - silence_start) >= min_silence_duration_samples:
                            # End of speech detected
                            if (silence_start - current_speech_start) >= min_speech_duration_samples:
                                speech_timestamps.append({
                                    'start': current_speech_start,
                                    'end': silence_start
                                })
                            current_speech_start = None
                            silence_start = None

            # Handle final segment
            if current_speech_start is not None:
                end = silence_start if silence_start is not None else len(audio)
                if (end - current_speech_start) >= min_speech_duration_samples:
                    speech_timestamps.append({
                        'start': current_speech_start,
                        'end': end
                    })

            # Convert samples to seconds
            segments = []
            for segment in speech_timestamps:
                start_sec = segment['start'] / sr
                end_sec = segment['end'] / sr
                segments.append((start_sec, end_sec))

            logging.info(f"Found {len(segments)} speech segments in {audio_path}")
            return segments

        except Exception as e:
            logging.error(f"Error segmenting audio {audio_path}: {e}")
            return self.simple_segmentation(audio_path)

    def simple_segmentation(self, audio_path):
        """
        Simplified segmentation when ONNX is not available
        This is a fallback implementation
        """
        try:
            import subprocess

            logging.info(f"Using simplified segmentation for {audio_path}")

            # Get audio duration using ffprobe
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip())

            # Return the full audio as one segment
            return [(0.0, duration)]

        except Exception as e:
            logging.error(f"Error in simple segmentation for {audio_path}: {e}")
            # Return default 30-second segment if all else fails
            return [(0.0, 30.0)]

    def extract_speech_segments(self, audio_path, output_dir=None):
        """
        Extract speech segments from audio file and save as separate files
        """
        if output_dir is None:
            output_dir = Path(audio_path).parent / "segments"
            output_dir.mkdir(exist_ok=True)

        segments = self.segment_audio(audio_path)

        extracted_files = []
        for i, (start_sec, end_sec) in enumerate(segments):
            base_name = Path(audio_path).stem
            output_path = output_dir / f"{base_name}_seg_{i:03d}.opus"

            try:
                # Use ffmpeg to extract the segment
                cmd = [
                    'ffmpeg', '-i', audio_path,
                    '-ss', str(start_sec),
                    '-to', str(end_sec),
                    '-c', 'copy',
                    '-y', str(output_path)
                ]

                subprocess.run(cmd, capture_output=True, check=True)
                extracted_files.append(str(output_path))
                logging.info(f"Extracted segment {i} to {output_path}")

            except Exception as e:
                logging.error(f"Error extracting segment {i}: {e}")
                # Return segment info even if extraction failed
                extracted_files.append(f"{audio_path}_seg_{i:03d}_({start_sec:.2f}s-{end_sec:.2f}s)")

        logging.info(f"Extracted {len(extracted_files)} speech segments from {audio_path}")
        return extracted_files

    def process_directory(self, input_dir, output_dir=None):
        """
        Process all audio files in a directory
        """
        input_path = Path(input_dir)
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = input_path / "segments"

        output_path.mkdir(exist_ok=True)

        # Find all audio files
        audio_files = list(input_path.glob("*.opus")) + list(input_path.glob("*.wav"))

        all_segments = {}
        for audio_file in audio_files:
            logging.info(f"Processing {audio_file}")
            segments = self.segment_audio(str(audio_file))
            all_segments[str(audio_file)] = segments

            # Extract segments if needed
            self.extract_speech_segments(str(audio_file), output_path)

        return all_segments


# Example usage
if __name__ == "__main__":
    vad_segmenter = VADSegmenter()

    # Example: Process a single audio file (if one exists)
    import sys
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        if os.path.exists(audio_file):
            segments = vad_segmenter.segment_audio(audio_file)
            print(f"Found segments: {segments}")
        else:
            print(f"Audio file {audio_file} not found")
    else:
        print("Provide an audio file path as an argument to test segmentation")
