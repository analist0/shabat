#!/usr/bin/env python3
"""
Voiseege Shabbat Mode Manager - Handles Shabbat compliance logic
"""

import json
import logging
from datetime import datetime, timedelta
from pytz import timezone

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/shabbat.log'),
        logging.StreamHandler()
    ]
)

class ShabbatManager:
    def __init__(self, config_path=None):
        import os
        # Determine the project root directory by looking for config.json in parent directories
        current_dir = os.path.dirname(os.path.abspath(__file__))  # This is the src directory
        project_root = os.path.dirname(current_dir)  # This should be the project root

        # If no config path is provided, use the default project config
        if config_path is None:
            self.config_path = os.path.join(project_root, "config.json")
        else:
            # If a config path is provided, check if it's relative to the project root
            if not os.path.isabs(config_path):
                self.config_path = os.path.join(project_root, config_path)
            else:
                self.config_path = config_path
        self.load_config()
        
        # Set timezone from config
        self.tz = timezone(self.config['shabbat']['timezone'])
        
        logging.info("Shabbat Manager initialized")

    def load_config(self):
        """Load configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        logging.info(f"Configuration loaded from {self.config_path}")

    def is_currently_shabbat(self):
        """
        Check if it's currently Shabbat based on timezone and schedule
        This is a simplified implementation - in a real system, you'd use 
        a proper Shabbat/Havdalah calculation library
        """
        now = datetime.now(self.tz)
        current_weekday = now.weekday()  # Monday is 0, Sunday is 6
        current_hour = now.hour
        current_minute = now.minute
        
        # For demonstration, assume Shabbat starts Friday evening and ends Saturday evening
        # This is a simplified calculation - real implementation would use astronomical calculations
        if current_weekday == 4:  # Friday
            # Check if after 6 PM (simplified candle lighting time)
            if current_hour >= self.config['shabbat']['shabbat_start_hour']:
                return True
        elif current_weekday == 5:  # Saturday
            # Check if before end time (simplified Havdalah time)
            if current_hour < self.config['shabbat']['shabbat_end_hour']:
                return True
        elif current_weekday == 6 and current_hour < 3:  # Sunday before 3 AM
            # If early Sunday, check if it was Shabbat until recently
            return True
        
        return False

    def get_next_shabbat_info(self):
        """Get information about the next Shabbat"""
        now = datetime.now(self.tz)
        
        # Find next Friday
        days_ahead = 4 - now.weekday()  # Friday is weekday 4
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        next_friday = now + timedelta(days=days_ahead)
        shabbat_start = next_friday.replace(
            hour=self.config['shabbat']['shabbat_start_hour'], 
            minute=0, 
            second=0, 
            microsecond=0
        )
        
        # Calculate end time (Saturday + config offset)
        shabbat_end = shabbat_start + timedelta(
            days=self.config['shabbat']['shabbat_end_day_offset'],
            hours=self.config['shabbat']['shabbat_end_hour'] - self.config['shabbat']['shabbat_start_hour']
        )
        
        return {
            "next_shabbat_start": shabbat_start.isoformat(),
            "next_shabbat_end": shabbat_end.isoformat(),
            "time_until_shabbat": (shabbat_start - now).total_seconds() if now < shabbat_start else 0
        }

    def get_current_shabbat_status(self):
        """Get comprehensive Shabbat status information"""
        is_shabbat = self.is_currently_shabbat()
        next_shabbat = self.get_next_shabbat_info()
        
        return {
            "is_shabbat": is_shabbat,
            "next_shabbat_info": next_shabbat,
            "current_time": datetime.now(self.tz).isoformat()
        }

    def can_perform_semantic_operation(self):
        """
        Check if semantic operations (transcription, analysis, etc.) are allowed
        These are forbidden during Shabbat
        """
        return not self.is_currently_shabbat()

    def can_write_semantic_data(self):
        """
        Check if writing semantic data (names, amounts, etc.) is allowed
        This is forbidden during Shabbat
        """
        return not self.is_currently_shabbat()


# Example usage
if __name__ == "__main__":
    shabbat_manager = ShabbatManager()
    
    status = shabbat_manager.get_current_shabbat_status()
    print(f"Is Shabbat: {status['is_shabbat']}")
    print(f"Current time: {status['current_time']}")
    print(f"Next Shabbat starts: {status['next_shabbat_info']['next_shabbat_start']}")
    
    print(f"Can perform semantic operations: {shabbat_manager.can_perform_semantic_operation()}")
    print(f"Can write semantic data: {shabbat_manager.can_write_semantic_data()}")