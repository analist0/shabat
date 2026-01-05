#!/usr/bin/env python3
"""
Voiseege System Utilities - Thermal management and system recovery features
"""

import os
import time
import json
import logging
import subprocess
import threading
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/system_utils.log'),
        logging.StreamHandler()
    ]
)

class SystemRecoveryManager:
    def __init__(self, config_path="../config.json"):
        self.config_path = config_path
        self.load_config()
        
        # Thermal management
        self.max_temp = self.config['system']['max_temperature']
        
        # Memory management
        self.memory_limit_mb = self.config['system']['memory_limit_mb']
        
        # File system integrity
        self.fs_check_interval = 3600  # Check every hour
        
        logging.info("System Recovery Manager initialized")

    def load_config(self):
        """Load configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        logging.info(f"Configuration loaded from {self.config_path}")

    def get_device_temperature(self):
        """
        Get device temperature
        Note: On Android/termux, this might not be directly available
        This is a placeholder implementation
        """
        try:
            # Try to get temperature from termux-sensors if available
            # This is just a placeholder - actual implementation would depend on available sensors
            result = subprocess.run(['termux-sensors', '-s'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Parse sensor data to find temperature
                # This is a simplified approach
                for line in result.stdout.split('\n'):
                    if 'temperature' in line.lower():
                        # Extract temperature value (this is just an example)
                        # Actual parsing would depend on termux-sensors output format
                        pass
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            # If termux-sensors is not available, try alternative methods
            # For now, return a simulated temperature
            pass
        
        # For now, return a simulated temperature
        # In a real implementation, you'd get this from system sensors
        return 35.0  # Simulated temperature in Celsius

    def check_thermal_limit(self):
        """Check if device temperature exceeds safe limits"""
        try:
            current_temp = self.get_device_temperature()
            logging.debug(f"Current device temperature: {current_temp}°C")
            
            if current_temp > self.max_temp:
                logging.warning(f"Temperature {current_temp}°C exceeds limit {self.max_temp}°C")
                return False  # Overheating
            return True  # Temperature is OK
        except Exception as e:
            logging.error(f"Error checking thermal limit: {e}")
            return True  # Assume OK if we can't check

    def thermal_management_loop(self):
        """Run thermal management in a loop"""
        logging.info("Starting thermal management loop")
        
        while True:
            if not self.check_thermal_limit():
                # Thermal limit exceeded - take action
                logging.warning("Thermal limit exceeded, pausing operations")
                
                # Pause recording and processing for a while
                time.sleep(60)  # Wait 1 minute before checking again
                continue
            
            # Wait before next check
            time.sleep(30)  # Check every 30 seconds

    def check_memory_usage(self):
        """Check memory usage of the process"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024  # Convert to MB
            
            logging.debug(f"Current memory usage: {memory_mb:.2f}MB")
            
            if memory_mb > self.memory_limit_mb:
                logging.warning(f"Memory usage {memory_mb:.2f}MB exceeds limit {self.memory_limit_mb}MB")
                return False  # Memory limit exceeded
            return True  # Memory usage is OK
        except ImportError:
            logging.warning("psutil not available, skipping memory check")
            return True  # Assume OK if we can't check
        except Exception as e:
            logging.error(f"Error checking memory usage: {e}")
            return True  # Assume OK if we can't check

    def force_restart_if_needed(self):
        """Force restart if needed based on system conditions"""
        # Check memory usage
        if not self.check_memory_usage():
            logging.critical("Memory limit exceeded, forcing restart...")
            self.force_restart()
        
        # Add other conditions that might require a restart
        # For example, file handle limits, disk space, etc.

    def force_restart(self):
        """Force restart the entire system"""
        import sys
        logging.critical("Performing system restart...")
        
        # Perform any cleanup if needed
        # Then restart
        os.execv(sys.executable, ['python'] + sys.argv)

    def check_filesystem_integrity(self):
        """Check filesystem integrity and repair if needed"""
        try:
            # Check if audio directory exists and is writable
            audio_dir = Path(self.config['paths']['audio_dir'])
            if not audio_dir.exists():
                logging.warning(f"Audio directory missing, recreating: {audio_dir}")
                audio_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if database file exists and is accessible
            db_path = Path(self.config['database']['path'])
            if not db_path.exists():
                logging.warning(f"Database file missing: {db_path}")
                # The database will be recreated when the DatabaseManager is initialized
            
            # Check for any pending operations that might have failed
            # This is where you'd check for any recovery files or pending operations
            
            logging.info("Filesystem integrity check passed")
            return True
        except Exception as e:
            logging.error(f"Filesystem integrity check failed: {e}")
            return False

    def filesystem_monitor_loop(self):
        """Run filesystem integrity checks in a loop"""
        logging.info("Starting filesystem monitor loop")
        
        while True:
            self.check_filesystem_integrity()
            
            # Wait for the next check
            time.sleep(self.fs_check_interval)

    def start_system_monitoring(self):
        """Start all system monitoring services in background threads"""
        # Start thermal management in a background thread
        thermal_thread = threading.Thread(target=self.thermal_management_loop, daemon=True)
        thermal_thread.start()
        
        # Start filesystem monitoring in a background thread
        fs_thread = threading.Thread(target=self.filesystem_monitor_loop, daemon=True)
        fs_thread.start()
        
        logging.info("System monitoring services started")

    def ensure_wake_lock(self):
        """Ensure the device stays awake during critical operations"""
        try:
            # On Android/termux, we can use termux-wake-lock
            result = subprocess.run(['termux-wake-lock'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logging.info("Wake lock acquired successfully")
                return True
            else:
                logging.error(f"Failed to acquire wake lock: {result.stderr}")
                return False
        except FileNotFoundError:
            logging.warning("termux-wake-lock not available")
            return False
        except Exception as e:
            logging.error(f"Error acquiring wake lock: {e}")
            return False

    def release_wake_lock(self):
        """Release the wake lock when no longer needed"""
        try:
            # On Android/termux, we can use termux-wake-unlock
            result = subprocess.run(['termux-wake-unlock'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logging.info("Wake lock released successfully")
                return True
            else:
                logging.error(f"Failed to release wake lock: {result.stderr}")
                return False
        except FileNotFoundError:
            logging.warning("termux-wake-unlock not available")
            return False
        except Exception as e:
            logging.error(f"Error releasing wake lock: {e}")
            return False


# Example usage
if __name__ == "__main__":
    recovery_manager = SystemRecoveryManager()
    
    # Start system monitoring
    recovery_manager.start_system_monitoring()
    
    # Keep the main thread alive
    try:
        while True:
            # Perform periodic checks
            recovery_manager.force_restart_if_needed()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logging.info("System recovery manager stopped")