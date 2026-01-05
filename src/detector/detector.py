#!/usr/bin/env python3
"""
Voiseege Aliyah Sale Detector - Detects and extracts aliyah sales from transcriptions
Uses rule-based detection first, then optional LLM verification
"""

import os
import json
import re
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/detector.log'),
        logging.StreamHandler()
    ]
)

class AliyahSaleDetector:
    def __init__(self, config_path="../../config.json"):
        # Adjust the config path to be relative to the project root
        import os
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
        self.load_config()
        
        # Hebrew keywords for aliyah sales
        self.hebrew_keywords = {
            # Aliyah types
            'torah': ['תורה', 'פרשת', 'פרשה', 'תורה'],
            'maftir': ['haftara', 'הפטרה', 'הפתר', 'הפטורה'],
            'bridegroom': ['חתן', 'כלה'],
            'ruler': ['长老', 'רuler', 'רולר'],  # Placeholder - need proper Hebrew
            
            # Sale indicators
            'sold': ['נמכר', 'נמכרה', 'נמכרו', 'נמכר'],
            'bought': ['קונה', 'קניתי', 'קנית', 'קנינו'],
            'for': ['בעד', 'בגין', 'לכבוד'],
            
            # Number words (Hebrew)
            'numbers': {
                'one': ['אחד', 'אחת'],
                'two': ['שנים', 'שתים'],
                'three': ['שלוש', 'שלושה'],
                'four': ['ארבע', 'ארבעה'],
                'five': ['חמש', 'חמישה'],
                'six': ['שש', 'שישה'],
                'seven': ['שבע', 'שבעה'],
                'hundred': ['מאה', 'מאות'],
                'thousand': ['אלף', 'אלפים']
            }
        }
        
        # Monetary keywords
        self.money_patterns = [
            r'(\d+)\s*(?:שקל|שקלים|NIS|nis)',  # NIS amounts
            r'(\d+)\s*(?:دولار|دولارا|USD|usd)',  # USD amounts (if needed)
            r'(\d+)\s*(?:€|ユーロ|euro)',  # EUR amounts (if needed)
        ]
        
        logging.info("Aliyah Sale Detector initialized")

    def load_config(self):
        """Load configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        logging.info(f"Configuration loaded from {self.config_path}")

    def extract_monetary_amounts(self, text):
        """Extract monetary amounts from text"""
        amounts = []
        
        for pattern in self.money_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount = float(match[0]) if isinstance(match, tuple) else float(match)
                    amounts.append(amount)
                except ValueError:
                    continue
        
        return amounts

    def extract_hebrew_names(self, text):
        """Extract potential Hebrew names from text"""
        # This is a simplified approach - in a real system, you'd use NLP
        # or a proper Hebrew name database
        
        # Common Hebrew name patterns
        name_patterns = [
            r'\b([א-ת]{2,})\s+(?:ben|בן|bat|בת)\s+([א-ת]{2,})',  # Name ben Name
            r'(?:Mr\.|Mrs\.|Ms\.)\s*([א-ת]{2,})',  # Title + Name
            r'\b([א-ת]{3,})\s+(?:the|Rabbi|rebbe|rebbe)\b',  # Name + title
        ]
        
        names = []
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    names.extend([name for name in match if name])
                else:
                    names.append(match)
        
        # Also look for capitalized Hebrew words that might be names
        hebrew_words = re.findall(r'[א-ת]{3,}', text)
        # Filter for potential names (this is a very basic approach)
        potential_names = [word for word in hebrew_words if len(word) >= 2]
        names.extend(potential_names)
        
        return list(set(names))  # Remove duplicates

    def detect_aliyah_type(self, text):
        """Detect the type of aliyah being sold"""
        text_lower = text.lower()
        
        # Check for specific aliyah types
        if any(keyword in text for keyword in self.hebrew_keywords['torah']):
            return 'torah'
        elif any(keyword in text for keyword in self.hebrew_keywords['maftir']):
            return 'maftir'
        elif any(keyword in text for keyword in self.hebrew_keywords['bridegroom']):
            return 'bridegroom'
        else:
            # Try to identify based on context
            aliyah_contexts = [
                ('torah', ['torah', 'parashat', 'parsha', 'פרשה', 'תורה']),
                ('maftir', ['haftara', 'haftarah', 'הפטרה']),
                ('ruler', ['ruler', '长老', 'רuler'])
            ]
            
            for aliyah_type, keywords in aliyah_contexts:
                if any(keyword in text_lower for keyword in keywords):
                    return aliyah_type
        
        return 'unknown'

    def calculate_confidence(self, detection_result):
        """Calculate confidence score for the detection"""
        score = 0
        
        # Points for different elements
        if detection_result.get('buyer_name'):
            score += 30
        if detection_result.get('aliyah_type') != 'unknown':
            score += 25
        if detection_result.get('amount'):
            score += 25
        if detection_result.get('timestamp'):
            score += 20
        
        # Additional points for multiple elements
        elements_present = sum([
            bool(detection_result.get('buyer_name')),
            detection_result.get('aliyah_type') != 'unknown',
            bool(detection_result.get('amount')),
            bool(detection_result.get('timestamp'))
        ])
        
        if elements_present >= 3:
            score += 20
        elif elements_present == 2:
            score += 10
        
        # Cap at 100
        return min(score, 100)

    def detect_aliyah_sales(self, transcription_data):
        """
        Detect aliyah sales from transcription data
        Returns list of detected sales with confidence scores
        """
        if isinstance(transcription_data, str):
            # If it's a file path, load the JSON
            if transcription_data.endswith('.json'):
                with open(transcription_data, 'r', encoding='utf-8') as f:
                    transcription_data = json.load(f)
            else:
                # If it's a raw string, wrap it
                transcription_data = {"text": transcription_data}
        
        text = transcription_data.get('text', '')
        segments = transcription_data.get('segments', [])
        
        detected_sales = []
        
        # Process the full text first
        sale = self._detect_sale_in_text(text, transcription_data.get('processing_time'))
        if sale:
            sale['confidence'] = self.calculate_confidence(sale)
            detected_sales.append(sale)
        
        # Process individual segments
        for segment in segments:
            segment_text = segment.get('text', '')
            segment_start = segment.get('start', 0)
            
            sale = self._detect_sale_in_text(segment_text, 
                                           transcription_data.get('processing_time'),
                                           segment_start)
            if sale:
                sale['confidence'] = self.calculate_confidence(sale)
                detected_sales.append(sale)
        
        return detected_sales

    def _detect_sale_in_text(self, text, processing_time=None, segment_start=0):
        """Internal method to detect a single sale in text"""
        if not text:
            return None
        
        # Extract monetary amounts
        amounts = self.extract_monetary_amounts(text)
        amount = amounts[0] if amounts else None  # Take the first amount found
        
        # Extract names
        names = self.extract_hebrew_names(text)
        buyer_name = names[0] if names else None  # Take the first name found
        
        # Detect aliyah type
        aliyah_type = self.detect_aliyah_type(text)
        
        # Check for sale indicators
        has_sale_indicator = any(
            keyword in text 
            for keyword_list in [
                self.hebrew_keywords['sold'], 
                self.hebrew_keywords['bought']
            ] 
            for keyword in keyword_list
        )
        
        # Only return if we have at least some confidence in the detection
        if buyer_name or amount or has_sale_indicator:
            return {
                "buyer_name": buyer_name,
                "aliyah_type": aliyah_type,
                "amount": amount,
                "timestamp": processing_time or datetime.now().isoformat(),
                "segment_start_time": segment_start,
                "text_snippet": text[:100] + "..." if len(text) > 100 else text
            }
        
        return None

    def process_transcription_directory(self, input_dir):
        """Process all transcription files in a directory"""
        input_path = Path(input_dir)
        
        # Find all JSON transcription files
        transcription_files = list(input_path.glob("*_transcription.json"))
        
        all_detections = {}
        for trans_file in transcription_files:
            logging.info(f"Processing transcription: {trans_file}")
            
            detections = self.detect_aliyah_sales(str(trans_file))
            all_detections[str(trans_file)] = detections
            
            logging.info(f"Found {len(detections)} potential sales in {trans_file}")
        
        return all_detections


# Example usage
if __name__ == "__main__":
    detector = AliyahSaleDetector()
    
    # Example transcription data
    sample_transcription = {
        "text": "Today we have a sale of the Torah aliyah for 300 shekels to Moshe ben Aharon",
        "segments": [
            {
                "start": 0.0,
                "end": 5.0,
                "text": "Today we have a sale"
            },
            {
                "start": 5.0,
                "end": 10.0,
                "text": "of the Torah aliyah for 300 shekels to Moshe ben Aharon"
            }
        ],
        "processing_time": datetime.now().isoformat()
    }
    
    detections = detector.detect_aliyah_sales(sample_transcription)
    print(f"Detected {len(detections)} sales:")
    for i, sale in enumerate(detections):
        print(f"  Sale {i+1}: {sale}")