#!/usr/bin/env python3
"""
Voiseege Audio Clipper - חיתוך קטעי אודיו של מכירות עליות
מחלץ את הקטע המדויק של כל מכירה ושומר אותו כקובץ נפרד
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
        logging.FileHandler('./logs/audio_clipper.log'),
        logging.StreamHandler()
    ]
)

class AudioClipper:
    def __init__(self, config_path="../../config.json"):
        # Adjust the config path to be relative to the project root
        import os
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
        self.load_config()

        # Create sales clips directory
        self.sales_clips_dir = Path("./audio/sales")
        self.sales_clips_dir.mkdir(parents=True, exist_ok=True)

        logging.info("Audio Clipper initialized")

    def load_config(self):
        """Load configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        logging.info(f"Configuration loaded from {self.config_path}")

    def extract_sale_clip(self, audio_path, start_time, end_time=None, duration=None, sale_id=None, buyer_name=None):
        """
        חילוץ קטע אודיו של מכירה ספציפית

        Args:
            audio_path: נתיב לקובץ האודיו המקורי
            start_time: זמן התחלה בשניות
            end_time: זמן סיום בשניות (אופציונלי)
            duration: משך הקטע בשניות (אופציונלי, במקום end_time)
            sale_id: מזהה המכירה (לשם הקובץ)
            buyer_name: שם הקונה (לשם הקובץ)

        Returns:
            str: נתיב לקובץ הקטע שנוצר
        """
        try:
            # חישוב זמן סיום
            if end_time is None and duration is not None:
                end_time = start_time + duration
            elif end_time is None:
                # ברירת מחדל: 30 שניות
                end_time = start_time + 30

            # יצירת שם קובץ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if sale_id:
                filename = f"sale_{sale_id}_{timestamp}.opus"
            elif buyer_name:
                # ניקוי שם הקונה לשם קובץ תקין
                safe_name = self._sanitize_filename(buyer_name)
                filename = f"sale_{safe_name}_{timestamp}.opus"
            else:
                filename = f"sale_{timestamp}.opus"

            output_path = self.sales_clips_dir / filename

            # חילוץ הקטע באמצעות ffmpeg
            cmd = [
                'ffmpeg',
                '-i', audio_path,
                '-ss', str(start_time),
                '-to', str(end_time),
                '-c', 'copy',  # העתקה ללא קידוד מחדש (מהיר)
                '-y',  # דריסת קובץ קיים
                str(output_path)
            ]

            logging.info(f"Extracting sale clip: {filename}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                # בדיקה שהקובץ נוצר בהצלחה
                if output_path.exists() and output_path.stat().st_size > 0:
                    file_size = output_path.stat().st_size / 1024  # KB
                    logging.info(f"✓ Sale clip created: {filename} ({file_size:.1f} KB)")
                    return str(output_path)
                else:
                    logging.error(f"Clip file was not created or is empty: {filename}")
                    return None
            else:
                logging.error(f"FFmpeg failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logging.error(f"Clip extraction timed out for {audio_path}")
            return None
        except Exception as e:
            logging.error(f"Error extracting sale clip: {e}")
            return None

    def extract_precise_clip(self, audio_path, start_time, end_time, sale_id=None, buyer_name=None):
        """
        חילוץ קטע מדויק עם קידוד מחדש (לדיוק גבוה יותר)

        שימוש כאשר צריך דיוק מדויק של התחלה וסוף
        """
        try:
            # יצירת שם קובץ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if sale_id:
                filename = f"sale_{sale_id}_{timestamp}_precise.opus"
            elif buyer_name:
                safe_name = self._sanitize_filename(buyer_name)
                filename = f"sale_{safe_name}_{timestamp}_precise.opus"
            else:
                filename = f"sale_{timestamp}_precise.opus"

            output_path = self.sales_clips_dir / filename

            # חילוץ עם קידוד מחדש לדיוק
            cmd = [
                'ffmpeg',
                '-i', audio_path,
                '-ss', str(start_time),
                '-to', str(end_time),
                '-c:a', 'libopus',  # קידוד מחדש ל-Opus
                '-b:a', '32k',  # bitrate נמוך
                '-vbr', 'on',
                '-y',
                str(output_path)
            ]

            logging.info(f"Extracting precise sale clip: {filename}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0 and output_path.exists():
                file_size = output_path.stat().st_size / 1024
                logging.info(f"✓ Precise clip created: {filename} ({file_size:.1f} KB)")
                return str(output_path)
            else:
                logging.error(f"Precise clip extraction failed: {result.stderr}")
                return None

        except Exception as e:
            logging.error(f"Error extracting precise clip: {e}")
            return None

    def get_audio_duration(self, audio_path):
        """קבלת משך האודיו בשניות"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            else:
                logging.error(f"Failed to get audio duration: {result.stderr}")
                return None

        except Exception as e:
            logging.error(f"Error getting audio duration: {e}")
            return None

    def extract_clip_with_context(self, audio_path, event_time, context_before=5, context_after=10,
                                   sale_id=None, buyer_name=None):
        """
        חילוץ קטע עם הקשר - כולל כמה שניות לפני ואחרי האירוע

        Args:
            audio_path: נתיב לאודיו
            event_time: זמן האירוע המרכזי
            context_before: שניות לפני האירוע
            context_after: שניות אחרי האירוע
            sale_id: מזהה מכירה
            buyer_name: שם קונה
        """
        start_time = max(0, event_time - context_before)

        # בדיקת משך האודיו
        duration = self.get_audio_duration(audio_path)
        if duration:
            end_time = min(duration, event_time + context_after)
        else:
            end_time = event_time + context_after

        return self.extract_sale_clip(
            audio_path,
            start_time,
            end_time=end_time,
            sale_id=sale_id,
            buyer_name=buyer_name
        )

    def _sanitize_filename(self, name):
        """
        ניקוי שם לשם קובץ תקין
        מסיר תווים בלתי חוקיים ומגביל אורך
        """
        if not name:
            return "unknown"

        # החלפת תווים בלתי חוקיים
        safe_name = name.replace('/', '_').replace('\\', '_').replace(' ', '_')
        safe_name = safe_name.replace('?', '').replace('*', '').replace(':', '_')
        safe_name = safe_name.replace('"', '').replace('<', '').replace('>', '')
        safe_name = safe_name.replace('|', '_')

        # הגבלת אורך
        if len(safe_name) > 50:
            safe_name = safe_name[:50]

        return safe_name

    def batch_extract_clips(self, sales_list):
        """
        חילוץ קטעים של רשימת מכירות

        Args:
            sales_list: רשימה של dict עם המפתחות:
                - audio_path: נתיב לאודיו
                - start_time: זמן התחלה
                - end_time או duration: זמן סיום או משך
                - sale_id: מזהה (אופציונלי)
                - buyer_name: שם קונה (אופציונלי)

        Returns:
            list: רשימת נתיבים לקטעים שנוצרו
        """
        clips = []

        for sale in sales_list:
            clip_path = self.extract_sale_clip(
                audio_path=sale.get('audio_path'),
                start_time=sale.get('start_time'),
                end_time=sale.get('end_time'),
                duration=sale.get('duration'),
                sale_id=sale.get('sale_id'),
                buyer_name=sale.get('buyer_name')
            )

            if clip_path:
                clips.append(clip_path)

        logging.info(f"Batch extraction completed: {len(clips)}/{len(sales_list)} clips created")
        return clips


# Example usage
if __name__ == "__main__":
    clipper = AudioClipper()

    # דוגמה: חילוץ קטע
    clip_path = clipper.extract_sale_clip(
        audio_path="./audio/test.opus",
        start_time=10.5,
        end_time=25.3,
        sale_id=123,
        buyer_name="משה כהן"
    )

    if clip_path:
        print(f"✓ Clip created: {clip_path}")
    else:
        print("✗ Failed to create clip")
