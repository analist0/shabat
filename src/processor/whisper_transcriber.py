#!/usr/bin/env python3
"""
Voiseege Whisper Transcription Module - Uses whisper.cpp for local STT
"""

import os
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/transcription.log'),
        logging.StreamHandler()
    ]
)

class WhisperTranscriber:
    def __init__(self, config_path="../../config.json"):
        # Adjust the config path to be relative to the project root
        import os
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
        self.load_config()

        # Verify whisper.cpp is available
        self.verify_whisper_cpp()

        logging.info("Whisper Transcriber initialized")

    def load_config(self):
        """Load configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        logging.info(f"Configuration loaded from {self.config_path}")

    def verify_whisper_cpp(self):
        """Verify that whisper.cpp is properly installed and accessible"""
        try:
            # Check if whisper.cpp main executable exists
            whisper_main = Path(self.config['whisper']['model_path']).parent / "main"

            if not whisper_main.exists():
                # Try common locations for whisper.cpp
                possible_paths = [
                    "./whisper.cpp/main",
                    "../whisper.cpp/main",
                    "~/whisper.cpp/main",
                    "/data/data/com.termux/files/usr/bin/whisper"
                ]

                found = False
                for path in possible_paths:
                    if Path(path).exists():
                        whisper_main = Path(path)
                        found = True
                        break

                if not found:
                    logging.warning("whisper.cpp main executable not found, transcription will be simulated")
                    self.whisper_cpp_path = None
                    return

            self.whisper_cpp_path = str(whisper_main)
            logging.info(f"Found whisper.cpp at: {self.whisper_cpp_path}")
        except Exception as e:
            logging.error(f"Error verifying whisper.cpp: {e}")
            self.whisper_cpp_path = None

    def transcribe_audio(self, audio_path, output_path=None):
        """
        Transcribe audio file using whisper.cpp
        Returns transcription result
        """
        if self.whisper_cpp_path is None:
            # Fallback when whisper.cpp is not available
            logging.warning("whisper.cpp not available, using simulated transcription")
            return self.simulate_transcription(audio_path)

        try:
            if output_path is None:
                # Create a temporary output file for the transcription
                output_path = Path(audio_path).with_suffix('.json')

            # Build the whisper.cpp command
            cmd = [
                self.whisper_cpp_path,
                "-m", self.config['whisper']['model_path'],
                "-l", self.config['whisper']['language'],
                "-bs", str(self.config['whisper']['beam_size']),
                "--word_timestamps", str(self.config['whisper']['word_timestamps']).lower(),
                "-f", audio_path,
                "-oj"  # Output in JSON format
            ]

            logging.info(f"Running whisper.cpp: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                logging.error(f"Whisper.cpp failed: {result.stderr}")
                return None

            # Parse the JSON output
            transcription_data = json.loads(result.stdout)

            # Calculate confidence as average of segment confidences
            total_confidence = 0
            segment_count = 0

            for segment in transcription_data.get('segments', []):
                total_confidence += segment.get('avg_logprob', 0)
                segment_count += 1

            avg_confidence = total_confidence / segment_count if segment_count > 0 else 0

            transcription_result = {
                "text": transcription_data.get('text', ''),
                "language": transcription_data.get('language', ''),
                "duration": transcription_data.get('duration', 0),
                "avg_confidence": avg_confidence,
                "segments": transcription_data.get('segments', []),
                "processing_time": datetime.now().isoformat()
            }

            logging.info(f"Transcription completed for {audio_path}")
            return transcription_result

        except subprocess.TimeoutExpired:
            logging.error(f"Transcription timed out for {audio_path}")
            return None
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON output from whisper.cpp for {audio_path}")
            return None
        except Exception as e:
            logging.error(f"Error transcribing {audio_path}: {e}")
            return None

    def simulate_transcription(self, audio_path):
        """
        Simulate transcription when whisper.cpp is not available
        This is a fallback implementation
        """
        try:
            # Create a simulated transcription result
            # In a real implementation, you might use a different approach
            # or return an error that can be handled by the calling code
            logging.info(f"Simulating transcription for {audio_path}")

            # Simulated result - in a real system, you might want to
            # return a more meaningful default or handle this differently
            simulated_result = {
                "text": "Simulated transcription - whisper.cpp not available",
                "language": self.config['whisper']['language'],
                "duration": 30.0,  # Assume 30 second duration
                "avg_confidence": 0.0,  # No confidence since it's simulated
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 30.0,
                        "text": "Simulated transcription - whisper.cpp not available",
                        "avg_logprob": 0.0
                    }
                ],
                "processing_time": datetime.now().isoformat()
            }

            return simulated_result
        except Exception as e:
            logging.error(f"Error in simulated transcription for {audio_path}: {e}")
            return None

    def transcribe_directory(self, input_dir, output_dir=None):
        """
        Transcribe all audio files in a directory
        """
        input_path = Path(input_dir)
        
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = input_path / "transcriptions"
        
        output_path.mkdir(exist_ok=True)
        
        # Find all audio files
        audio_files = list(input_path.glob("*.opus")) + list(input_path.glob("*.wav"))
        
        results = {}
        for audio_file in audio_files:
            logging.info(f"Transcribing {audio_file}")
            
            # Create output file path
            output_file = output_path / f"{audio_file.stem}_transcription.json"
            
            result = self.transcribe_audio(str(audio_file), str(output_file))
            results[str(audio_file)] = result
            
            if result:
                # Save the result to the specified output file
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
        
        return results


# Example usage
if __name__ == "__main__":
    transcriber = WhisperTranscriber()
    
    # Example: Transcribe a single audio file (if one exists)
    import sys
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        if os.path.exists(audio_file):
            result = transcriber.transcribe_audio(audio_file)
            if result:
                print(f"Transcription: {result['text']}")
                print(f"Confidence: {result['avg_confidence']:.2f}")
            else:
                print(f"Transcription failed for {audio_file}")
        else:
            print(f"Audio file {audio_file} not found")
    else:
        print("Provide an audio file path as an argument to test transcription")