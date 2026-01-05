#!/usr/bin/env python3
"""
Voiseege Aliyah Sale Detector - מנוע זיהוי משופר למכירות עליות
זיהוי מתקדם של סכומים, שמות וסוגי עליות בעברית
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

        # מילון מספרים בעברית - המרה למספרים
        self.hebrew_numbers = {
            # יחידות
            'אפס': 0, 'אחת': 1, 'אחד': 1, 'שתיים': 2, 'שניים': 2, 'שנים': 2,
            'שלוש': 3, 'שלושה': 3, 'ארבע': 4, 'ארבעה': 4, 'חמש': 5, 'חמישה': 5,
            'שש': 6, 'שישה': 6, 'שבע': 7, 'שבעה': 7, 'שמונה': 8, 'שמונה': 8,
            'תשע': 9, 'תשעה': 9, 'עשר': 10, 'עשרה': 10,

            # עשרות
            'עשרים': 20, 'שלושים': 30, 'ארבעים': 40, 'חמישים': 50,
            'שישים': 60, 'שבעים': 70, 'שמונים': 80, 'תשעים': 90,

            # מאות
            'מאה': 100, 'מאתיים': 200, 'מאתים': 200, 'שלוש מאות': 300, 'שלושמאות': 300,
            'ארבע מאות': 400, 'ארבעמאות': 400, 'חמש מאות': 500, 'חמשמאות': 500,
            'שש מאות': 600, 'ששמאות': 600, 'שבע מאות': 700, 'שבעמאות': 700,
            'שמונה מאות': 800, 'שמונהמאות': 800, 'תשע מאות': 900, 'תשעמאות': 900,

            # אלפים
            'אלף': 1000, 'אלפיים': 2000, 'שלושת אלפים': 3000, 'ארבעת אלפים': 4000,
            'חמשת אלפים': 5000
        }

        # מילות מפתח למכירה
        self.sale_keywords = {
            'sold': ['נמכר', 'נמכרה', 'נמכרו', 'מוכר', 'מוכרת', 'נקנה', 'נקנתה'],
            'bought': ['קונה', 'קנה', 'רכש', 'זכה'],
            'for_price': ['בעד', 'בגין', 'לכבוד', 'תמורת', 'במחיר', 'בסכום'],
            'amount_words': ['שקל', 'שקלים', 'ש"ח', 'שח', 'ניו', 'NIS']
        }

        # סוגי עליות
        self.aliyah_types = {
            'כהן': 'kohen',
            'לוי': 'levi',
            'שלישי': 'shlishi',
            'רביעי': 'revii',
            'חמישי': 'chamishi',
            'ששי': 'shishi',
            'שביעי': 'shvii',
            'מפטיר': 'maftir',
            'הפטרה': 'haftara',
            'חתן': 'chatan_torah',
            'בראשית': 'chatan_bereshit',
            'תורה': 'general_aliyah'
        }

        # דפוסי שמות עבריים נפוצים
        self.name_prefixes = ['רבי', 'הרב', 'מר', 'גברת', 'הגב', 'ר', 'הר']
        self.name_suffixes = ['בן', 'בת', 'הכהן', 'הלוי']

        logging.info("Enhanced Aliyah Sale Detector initialized")

    def load_config(self):
        """Load configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        logging.info(f"Configuration loaded from {self.config_path}")

    def parse_hebrew_number(self, text):
        """
        המרת מספר מדובר בעברית למספר
        לדוגמה: "שלוש מאות חמישים" -> 350
        """
        text = text.strip().lower()

        # בדיקה ישירה במילון
        if text in self.hebrew_numbers:
            return self.hebrew_numbers[text]

        # ניסיון לפרק מספר מורכב
        total = 0
        current_number = 0

        words = text.split()
        for word in words:
            if word in self.hebrew_numbers:
                value = self.hebrew_numbers[word]

                # אם זה מאות או אלפים, הכפל את הערך הנוכחי
                if value >= 100:
                    if current_number > 0:
                        total += current_number * value
                        current_number = 0
                    else:
                        total += value
                else:
                    current_number += value
            elif word in ['ו', 'ו-']:  # מילת חיבור
                continue

        # הוסף את מה שנשאר
        total += current_number

        return total if total > 0 else None

    def extract_monetary_amounts(self, text):
        """
        חילוץ סכומים כספיים מטקסט - גם ספרות וגם מילים
        """
        amounts = []

        # Pattern 1: ספרות עם מילת מטבע
        patterns = [
            r'(\d{1,5})\s*(?:שקל|שקלים|ש"ח|שח|NIS)',
            r'(?:שקל|שקלים|ש"ח|שח)\s*(\d{1,5})',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount = float(match)
                    if amount > 0 and amount < 100000:  # בדיקת תקינות
                        amounts.append(amount)
                except (ValueError, TypeError):
                    continue

        # Pattern 2: מספרים מדוברים בעברית
        # "שלוש מאות שקל", "מאתיים וחמישים שקלים"
        hebrew_amount_pattern = r'((?:[א-ת]+\s*){1,6})(?:שקל|שקלים|ש"ח)'

        matches = re.findall(hebrew_amount_pattern, text)
        for match in matches:
            parsed = self.parse_hebrew_number(match)
            if parsed and parsed > 0 and parsed < 100000:
                amounts.append(float(parsed))

        # Pattern 3: שילוב ספרות ומילים
        # "300 שקל", "חמש מאות ש"ח"
        mixed_patterns = [
            r'(\d+)\s*(?:שקל|שקלים|ש"ח)',
            r'((?:[א-ת]+\s*)+)\s*(\d+)',  # "מאתיים 50"
        ]

        for pattern in mixed_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    if isinstance(match, tuple):
                        # נסה את החלק הראשון
                        for part in match:
                            if part.strip().isdigit():
                                amounts.append(float(part))
                            else:
                                parsed = self.parse_hebrew_number(part)
                                if parsed:
                                    amounts.append(float(parsed))
                    else:
                        amounts.append(float(match))
                except (ValueError, TypeError):
                    continue

        # הסרת כפילויות והחזרת הסכום הגבוה ביותר (לרוב זה הנכון)
        if amounts:
            return list(set(amounts))
        return []

    def extract_hebrew_names(self, text):
        """
        חילוץ שמות עבריים מטקסט - משופר
        """
        names = []

        # Pattern 1: שם + בן/בת + שם
        pattern_ben = r'\b([א-ת]{2,})\s+(?:בן|בת)\s+([א-ת]{2,})\b'
        matches = re.findall(pattern_ben, text)
        for match in matches:
            full_name = f"{match[0]} בן {match[1]}"
            names.append(full_name)

        # Pattern 2: תואר + שם (רבי/מר/הרב + שם)
        for prefix in self.name_prefixes:
            pattern = f'{prefix}\\s+([א-ת]{{2,}}(?:\\s+[א-ת]{{2,}})?)'
            matches = re.findall(pattern, text)
            names.extend(matches)

        # Pattern 3: שם + תואר (כהן/לוי)
        for suffix in self.name_suffixes:
            pattern = f'([א-ת]{{2,}})\\s+{suffix}'
            matches = re.findall(pattern, text)
            names.extend(matches)

        # Pattern 4: שמות בודדים (2-15 תווים עבריים)
        # מחפש מילים עבריות שנראות כמו שמות
        words = re.findall(r'\b[א-ת]{2,15}\b', text)

        # סינון: רק מילים שמתחילות באות גדולה או שהן בהקשר של מכירה
        potential_names = []
        for word in words:
            # בדוק שזו לא מילת מפתח
            if word not in self.sale_keywords['sold'] and \
               word not in self.sale_keywords['bought'] and \
               word not in self.aliyah_types.keys() and \
               len(word) >= 2:
                potential_names.append(word)

        names.extend(potential_names)

        # הסרת כפילויות ושמות לא תקינים
        unique_names = []
        for name in names:
            if name and name not in unique_names and len(name) >= 2:
                unique_names.append(name)

        return unique_names[:5]  # מגביל ל-5 שמות הטובים ביותר

    def detect_aliyah_type(self, text):
        """זיהוי סוג העלייה מהטקסט"""
        text_lower = text.lower()

        # מעבר על כל סוגי העליות
        for hebrew_name, english_type in self.aliyah_types.items():
            if hebrew_name in text_lower:
                return english_type

        # דפוסים נוספים
        if any(word in text_lower for word in ['עולה', 'עלייה']):
            # ניסיון לזהות לפי מספר
            numbers = re.findall(r'(?:עלייה|עולה)\s*(?:מספר)?\s*(\d+|[א-ת]+)', text_lower)
            if numbers:
                return f'aliyah_{numbers[0]}'

        return 'unknown'

    def calculate_confidence(self, detection_result):
        """
        חישוב ציון ביטחון לזיהוי - משופר
        """
        score = 0

        # בדיקות בסיסיות
        has_name = bool(detection_result.get('buyer_name'))
        has_type = detection_result.get('aliyah_type') != 'unknown'
        has_amount = detection_result.get('amount') is not None
        has_sale_keyword = detection_result.get('has_sale_keyword', False)

        # ניקוד לפי רכיבים
        if has_name:
            score += 30
        if has_type:
            score += 25
        if has_amount:
            score += 30  # סכום הוא מאוד חשוב
        if has_sale_keyword:
            score += 15  # מילת מכירה מגבירה ביטחון

        # בונוס אם יש שילוב של מספר רכיבים
        elements_count = sum([has_name, has_type, has_amount, has_sale_keyword])

        if elements_count >= 3:
            score += 20
        elif elements_count == 2:
            score += 10

        # בונוס לפי איכות הזיהוי
        if has_amount and has_name:
            score += 10  # שילוב של שם וסכום

        # הפחתה אם חסרים רכיבים קריטיים
        if not has_amount:
            score -= 20

        return min(max(score, 0), 100)  # הגבלה בין 0-100

    def detect_aliyah_sales(self, transcription_data):
        """
        זיהוי מכירות עליות מתמלול - משופר
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

        # עיבוד הטקסט המלא
        sale = self._detect_sale_in_text(
            text,
            transcription_data.get('processing_time'),
            segment_start=0
        )
        if sale:
            sale['confidence'] = self.calculate_confidence(sale)
            if sale['confidence'] >= 30:  # סף מינימום
                detected_sales.append(sale)

        # עיבוד סגמנטים בודדים
        for segment in segments:
            segment_text = segment.get('text', '')
            segment_start = segment.get('start', 0)

            sale = self._detect_sale_in_text(
                segment_text,
                transcription_data.get('processing_time'),
                segment_start
            )

            if sale:
                sale['confidence'] = self.calculate_confidence(sale)
                if sale['confidence'] >= 30:
                    detected_sales.append(sale)

        # הסרת כפילויות (מכירות שזוהו גם בטקסט המלא וגם בסגמנט)
        unique_sales = self._remove_duplicate_sales(detected_sales)

        logging.info(f"Detected {len(unique_sales)} potential aliyah sales")
        return unique_sales

    def _detect_sale_in_text(self, text, processing_time=None, segment_start=0):
        """זיהוי פנימי של מכירה בטקסט"""
        if not text or len(text) < 5:
            return None

        # חילוץ סכומים
        amounts = self.extract_monetary_amounts(text)
        amount = amounts[0] if amounts else None

        # חילוץ שמות
        names = self.extract_hebrew_names(text)
        buyer_name = names[0] if names else None

        # זיהוי סוג עלייה
        aliyah_type = self.detect_aliyah_type(text)

        # בדיקת מילות מכירה
        has_sale_indicator = any(
            keyword in text
            for keyword_list in [
                self.sale_keywords['sold'],
                self.sale_keywords['bought']
            ]
            for keyword in keyword_list
        )

        # רק אם יש לפחות 2 מתוך: סכום/שם/מילת_מכירה
        elements = [amount is not None, buyer_name is not None, has_sale_indicator]
        if sum(elements) < 2:
            return None

        return {
            "buyer_name": buyer_name,
            "aliyah_type": aliyah_type,
            "amount": amount,
            "timestamp": processing_time or datetime.now().isoformat(),
            "segment_start_time": segment_start,
            "text_snippet": text[:200] + "..." if len(text) > 200 else text,
            "has_sale_keyword": has_sale_indicator
        }

    def _remove_duplicate_sales(self, sales):
        """הסרת מכירות כפולות"""
        if len(sales) <= 1:
            return sales

        unique = []
        for sale in sales:
            is_duplicate = False

            for existing in unique:
                # בדיקת דמיון
                same_amount = sale.get('amount') == existing.get('amount')
                same_name = sale.get('buyer_name') == existing.get('buyer_name')
                close_time = abs(sale.get('segment_start_time', 0) -
                               existing.get('segment_start_time', 0)) < 5

                if same_amount and (same_name or close_time):
                    is_duplicate = True
                    # שמור את הגרסה עם הביטחון הגבוה יותר
                    if sale.get('confidence', 0) > existing.get('confidence', 0):
                        unique.remove(existing)
                        unique.append(sale)
                    break

            if not is_duplicate:
                unique.append(sale)

        return unique


# Example usage
if __name__ == "__main__":
    detector = AliyahSaleDetector()

    # דוגמאות לבדיקה
    test_cases = [
        "נמכרה עלייה שלישית למר משה כהן בעד שלוש מאות שקל",
        "קונה דוד לוי עלייה רביעית תמורת 250 שקלים",
        "מפטיר נמכר לרבי יוסף בן אברהם במחיר של חמש מאות ש\"ח",
        "חתן תורה זכה בה אליהו הכהן בסכום 400 שקל"
    ]

    for i, text in enumerate(test_cases, 1):
        print(f"\n=== Test {i} ===")
        print(f"Input: {text}")

        transcription = {
            "text": text,
            "processing_time": datetime.now().isoformat()
        }

        sales = detector.detect_aliyah_sales(transcription)

        if sales:
            for sale in sales:
                print(f"✓ Detected: {sale['buyer_name']} | "
                      f"{sale['aliyah_type']} | "
                      f"{sale['amount']} ₪ | "
                      f"Confidence: {sale.get('confidence', 0):.0f}%")
        else:
            print("✗ No sale detected")
