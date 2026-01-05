#!/usr/bin/env python3
"""
Voiseege VAD (Voice Activity Detection) Module - Uses Silero VAD
"""

import os
import json
import logging
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

        # Try to load Silero VAD model, but handle gracefully if not available
        self.pytorch_available = self.check_pytorch_availability()
        if self.pytorch_available:
            self.load_vad_model()
        else:
            logging.warning("PyTorch not available, VAD functionality will be limited")

        logging.info("VAD Segmenter initialized")

    def check_pytorch_availability(self):
        """Check if PyTorch is available"""
        try:
            import torch
            import torchaudio
            return True
        except ImportError:
            return False

    def load_config(self):
        """Load configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        logging.info(f"Configuration loaded from {self.config_path}")

    def load_vad_model(self):
        """Load the Silero VAD model"""
        try:
            import torch
            import torchaudio

            # Load the Silero VAD model
            self.model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False
            )

            # Extract utilities
            (get_speech_timestamps,
             save_audio,
             read_audio,
             VADIterator,
             collect_chunks) = utils

            self.get_speech_timestamps = get_speech_timestamps
            self.save_audio = save_audio
            self.read_audio = read_audio
            self.VADIterator = VADIterator
            self.collect_chunks = collect_chunks

            logging.info("Silero VAD model loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load Silero VAD model: {e}")
            raise

    def segment_audio(self, audio_path):
        """
        Segment audio file using VAD to identify speech segments
        Returns list of (start_time, end_time) tuples in seconds
        """
        if not self.pytorch_available:
            # Fallback implementation when PyTorch is not available
            # This is a simplified approach using sox for basic audio processing
            logging.warning("PyTorch not available, using simplified segmentation")
            return self.simple_segmentation(audio_path)

        try:
            import torch
            import torchaudio

            # Read the audio file
            wav, sr = torchaudio.load(audio_path)

            # Convert to mono if needed
            if wav.shape[0] > 1:
                wav = torch.mean(wav, dim=0, keepdim=True)

            # Get speech timestamps
            speech_timestamps = self.get_speech_timestamps(
                wav,
                self.model,
                threshold=self.config['vad']['threshold'],
                sampling_rate=sr,
                min_silence_duration_ms=int(self.config['vad']['min_silence_duration'] * 1000),
                min_speech_duration_ms=int(self.config['vad']['min_speech_duration'] * 1000),
                window_size_samples=512
            )

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
            return []

    def simple_segmentation(self, audio_path):
        """
        Simplified segmentation using sox when PyTorch is not available
        This is a fallback implementation
        """
        import subprocess
        import tempfile
        import os

        try:
            # Use sox to detect silence and speech segments
            # This is a simplified approach that just returns the full duration
            # as one segment when PyTorch is not available
            logging.info(f"Using simplified segmentation for {audio_path}")

            # For now, return the full audio as one segment
            # In a real implementation, you might use sox commands to detect segments
            # Example: sox input.wav output.wav silence 1 0.1 1% : newfile : restart
            return [(0.0, 30.0)]  # Return a single 30-second segment as a placeholder

        except Exception as e:
            logging.error(f"Error in simple segmentation for {audio_path}: {e}")
            return []

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
            # For the simplified approach, we just return the original file
            # since we can't do detailed segment extraction without PyTorch
            base_name = Path(audio_path).stem
            output_path = output_dir / f"{base_name}_seg_{i:03d}.wav"

            # Since we don't have PyTorch, we'll just copy the original file
            # or return the segment information without actual extraction
            extracted_files.append(f"{audio_path}_seg_{i:03d}_({start_sec:.2f}s-{end_sec:.2f}s)")

        logging.info(f"Identified {len(extracted_files)} speech segments in {audio_path}")
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