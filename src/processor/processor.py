#!/usr/bin/env python3
"""
Voiseege Post-Shabbat Processing Pipeline
Handles VAD segmentation, transcription, and aliyah sale detection after Shabbat ends
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path

# Import our modules
import sys
import os

# Add the project root to the Python path to handle imports properly
project_root = os.path.dirname(os.path.dirname(__file__))  # This should be the project root
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add the src directory to the path for imports
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Add the current directory to the path to allow direct imports
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Add the detector directory to the path to allow direct imports
detector_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'detector')
if detector_dir not in sys.path:
    sys.path.insert(0, detector_dir)

from database import DatabaseManager
from shabbat_manager import ShabbatManager

# Import processor modules directly since we've added the paths
from vad_segmenter import VADSegmenter
from whisper_transcriber import WhisperTranscriber
from detector import AliyahSaleDetector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/processing_pipeline.log'),
        logging.StreamHandler()
    ]
)

class PostShabbatPipeline:
    def __init__(self, config_path="../../config.json"):
        # Adjust the config path to be relative to the project root
        import os
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
        self.load_config()
        
        # Initialize components
        self.db = DatabaseManager(self.config['database']['path'])
        self.shabbat_manager = ShabbatManager()
        self.vad_segmenter = VADSegmenter()
        self.transcriber = WhisperTranscriber()
        self.detector = AliyahSaleDetector()
        
        logging.info("Post-Shabbat Processing Pipeline initialized")

    def load_config(self):
        """Load configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        logging.info(f"Configuration loaded from {self.config_path}")

    def get_unprocessed_audio(self):
        """Get list of audio files that haven't been processed yet"""
        # In the database, we can check for audio files that don't have associated transcripts
        cursor = self.db.connection.cursor()
        
        # Get audio files without transcripts
        cursor.execute('''
            SELECT ra.id, ra.filepath, ra.recording_start
            FROM raw_audio ra
            LEFT JOIN transcripts t ON ra.id = t.audio_id
            WHERE t.audio_id IS NULL
            ORDER BY ra.recording_start
        ''')
        
        return cursor.fetchall()

    def process_audio_file(self, audio_id, audio_path):
        """Process a single audio file through the entire pipeline"""
        logging.info(f"Processing audio file: {audio_path} (ID: {audio_id})")
        
        try:
            # Step 1: VAD segmentation
            logging.info(f"Step 1: Segmenting audio with VAD")
            segments = self.vad_segmenter.segment_audio(audio_path)
            
            if not segments:
                logging.warning(f"No speech segments found in {audio_path}")
                return False
            
            # Step 2: Extract speech segments
            logging.info(f"Step 2: Identifying {len(segments)} speech segments")
            segment_files = self.vad_segmenter.extract_speech_segments(
                audio_path,
                output_dir=Path(audio_path).parent / "segments"
            )

            # Step 3: Transcribe each segment
            logging.info(f"Step 3: Transcribing {len(segment_files)} segments")
            all_transcripts = []
            total_confidence = 0
            segment_count = 0

            # For the simplified approach, we'll transcribe the entire audio file
            # rather than individual segments since we don't have PyTorch
            if segment_files:
                # Transcribe the original audio file
                transcription = self.transcriber.transcribe_audio(audio_path)
                if transcription:
                    all_transcripts.append(transcription)
                    total_confidence += transcription.get('avg_confidence', 0)
                    segment_count += 1
            
            if not all_transcripts:
                logging.warning(f"No successful transcriptions for {audio_path}")
                return False
            
            # Combine all transcriptions into one
            combined_text = " ".join([t['text'] for t in all_transcripts if t and t.get('text')])
            avg_confidence = total_confidence / segment_count if segment_count > 0 else 0
            
            # Create a combined transcription result
            combined_transcription = {
                "text": combined_text,
                "language": all_transcripts[0].get('language', 'he'),
                "duration": sum(t.get('duration', 0) for t in all_transcripts),
                "avg_confidence": avg_confidence,
                "segments": all_transcripts,
                "processing_time": datetime.now().isoformat()
            }
            
            # Step 4: Store transcription in database
            logging.info(f"Step 4: Storing transcription in database")
            transcript_id = self.db.insert_transcript(
                audio_id=audio_id,
                transcript=combined_transcription['text'],
                language=combined_transcription['language'],
                confidence=combined_transcription['avg_confidence']
            )
            
            # Step 5: Detect aliyah sales
            logging.info(f"Step 5: Detecting aliyah sales in transcription")
            sales = self.detector.detect_aliyah_sales(combined_transcription)
            
            # Step 6: Store detected sales in database
            logging.info(f"Step 6: Storing {len(sales)} detected sales in database")
            for sale in sales:
                # Find or create congregant
                congregant_id = self.find_or_create_congregant(sale.get('buyer_name', 'Unknown'))
                
                # Insert aliyah sale
                aliyah_sale_id = self.db.insert_aliyah_sale(
                    congregant_id=congregant_id,
                    aliyah_type=sale.get('aliyah_type', 'unknown'),
                    amount=sale.get('amount'),
                    timestamp=sale.get('timestamp'),
                    audio_id=audio_id,
                    transcript_id=transcript_id,
                    confidence=sale.get('confidence', 0)
                )
                
                logging.info(f"Stored aliyah sale: {sale.get('buyer_name', 'Unknown')} - {sale.get('amount', 'N/A')} NIS")
            
            logging.info(f"Successfully processed audio file: {audio_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error processing audio file {audio_path}: {e}")
            return False

    def find_or_create_congregant(self, name):
        """Find existing congregant or create new one"""
        if not name or name == 'Unknown':
            # Create an anonymous congregant
            name = f"Anonymous_{int(time.time())}"
        
        cursor = self.db.connection.cursor()
        
        # Try to find existing congregant
        cursor.execute("SELECT id FROM congregants WHERE name = ?", (name,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Create new congregant
        congregant_id = self.db.insert_congregant(name=name)
        return congregant_id

    def run_pipeline(self):
        """Run the entire post-Shabbat processing pipeline"""
        logging.info("Starting Post-Shabbat Processing Pipeline...")
        
        # Check if it's currently Shabbat - we shouldn't run during Shabbat
        if self.shabbat_manager.is_currently_shabbat():
            logging.warning("It's currently Shabbat, skipping processing")
            return
        
        # Get unprocessed audio files
        unprocessed_audio = self.get_unprocessed_audio()
        logging.info(f"Found {len(unprocessed_audio)} unprocessed audio files")
        
        processed_count = 0
        for audio_row in unprocessed_audio:
            audio_id, audio_path, recording_start = audio_row
            
            success = self.process_audio_file(audio_id, audio_path)
            if success:
                processed_count += 1
                logging.info(f"Completed processing for audio ID {audio_id}")
            else:
                logging.error(f"Failed to process audio ID {audio_id}")
        
        logging.info(f"Pipeline completed. Processed {processed_count} out of {len(unprocessed_audio)} files")
        
        # Close database connection
        self.db.close()

    def process_new_files_loop(self):
        """Run the pipeline in a loop, processing new files as they appear"""
        logging.info("Starting continuous processing loop...")
        
        while True:
            # Check if it's Shabbat - if so, wait and check again
            if self.shabbat_manager.is_currently_shabbat():
                logging.info("It's currently Shabbat, waiting before next check...")
                time.sleep(60)  # Wait 1 minute before checking again
                continue
            
            # Run the pipeline
            self.run_pipeline()
            
            # Wait before next check
            time.sleep(30)  # Wait 30 seconds before checking for new files


# Example usage
if __name__ == "__main__":
    pipeline = PostShabbatPipeline()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        # Run in continuous mode
        pipeline.process_new_files_loop()
    else:
        # Run once
        pipeline.run_pipeline()