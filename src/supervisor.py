#!/usr/bin/env python3
"""
Voiseege Supervisor - Main process manager for the audio intelligence system
Ensures all components run reliably and recover from failures
"""

import os
import sys
import json
import time
import signal
import subprocess
import threading
import logging
import psutil
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/supervisor.log'),
        logging.StreamHandler()
    ]
)

class Supervisor:
    def __init__(self, config_path="./config.json"):
        self.config_path = config_path
        self.load_config()

        # Process tracking
        self.processes = {}
        self.threads = {}
        self.running = True

        # Setup directories
        self.setup_directories()

        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Thermal monitoring
        self.max_temp = self.config['system']['max_temperature']

        # Memory monitoring
        self.restart_after_files = self.config['system']['restart_after_files']
        self.file_counter = 0

        # IO backpressure
        self.token_bucket = {'tokens': 10, 'max_tokens': 10, 'refill_rate': 1}  # Simple token bucket

        logging.info("Supervisor initialized")

    def load_config(self):
        """Load configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        logging.info(f"Configuration loaded from {self.config_path}")

    def setup_directories(self):
        """Create required directories"""
        dirs = [
            self.config['paths']['audio_dir'],
            self.config['paths']['log_dir'],
            self.config['paths']['model_dir']
        ]

        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logging.info(f"Ensured directory exists: {dir_path}")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logging.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False

    def check_thermal_limit(self):
        """Check if device temperature exceeds safe limits"""
        try:
            # On Android/termux, thermal info might not be directly available
            # This is a placeholder - actual implementation would depend on available sensors
            # For now, we'll just return True (safe) to continue operation
            # In a real implementation, we might use termux-sensors or other methods
            return True
        except Exception as e:
            logging.warning(f"Could not check thermal status: {e}")
            return True  # Assume safe if we can't check

    def check_memory_usage(self):
        """Check memory usage and restart if needed"""
        try:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024  # Convert to MB

            if memory_mb > self.config['system']['memory_limit_mb']:
                logging.warning(f"Memory usage {memory_mb:.2f}MB exceeds limit {self.config['system']['memory_limit_mb']}MB")
                return False  # Memory limit exceeded
            return True  # Memory usage is OK
        except Exception as e:
            logging.error(f"Error checking memory usage: {e}")
            return True  # Assume OK if we can't check

    def refill_token_bucket(self):
        """Refill the token bucket for IO backpressure"""
        self.token_bucket['tokens'] = min(
            self.token_bucket['max_tokens'],
            self.token_bucket['tokens'] + self.token_bucket['refill_rate']
        )

    def consume_token(self):
        """Consume a token from the bucket"""
        if self.token_bucket['tokens'] > 0:
            self.token_bucket['tokens'] -= 1
            return True
        return False

    def start_recorder(self):
        """Start the audio recorder process"""
        try:
            cmd = [
                sys.executable,
                "./src/recorder/recorder.py"
            ]

            # Add environment variables if needed
            env = os.environ.copy()
            env['PYTHONPATH'] = './src'

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=os.getcwd()  # Set the working directory to the project root
            )

            self.processes['recorder'] = process
            logging.info("Recorder process started with PID: {}".format(process.pid))

            return process
        except Exception as e:
            logging.error(f"Failed to start recorder: {e}")
            return None

    def start_processor(self):
        """Start the audio processor (VAD + transcription) process"""
        try:
            cmd = [
                sys.executable,
                "./src/processor/processor.py",
                "--continuous"  # Run in continuous mode
            ]

            # Add environment variables if needed
            env = os.environ.copy()
            env['PYTHONPATH'] = './src'

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=os.getcwd()  # Set the working directory to the project root
            )

            self.processes['processor'] = process
            logging.info("Processor process started with PID: {}".format(process.pid))

            return process
        except Exception as e:
            logging.error(f"Failed to start processor: {e}")
            return None

    def start_detector(self):
        """Start the aliyah sale detector process"""
        try:
            cmd = [
                sys.executable,
                "./src/detector/detector.py"
            ]

            # Add environment variables if needed
            env = os.environ.copy()
            env['PYTHONPATH'] = './src'

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=os.getcwd()  # Set the working directory to the project root
            )

            self.processes['detector'] = process
            logging.info("Detector process started with PID: {}".format(process.pid))

            return process
        except Exception as e:
            logging.error(f"Failed to start detector: {e}")
            return None

    def start_dashboard(self):
        """Start the dashboard API process"""
        try:
            cmd = [
                sys.executable,
                "./src/dashboard/server.py"
            ]

            # Add environment variables if needed
            env = os.environ.copy()
            env['PYTHONPATH'] = './src'

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=os.getcwd()  # Set the working directory to the project root
            )

            self.processes['dashboard'] = process
            logging.info("Dashboard process started with PID: {}".format(process.pid))

            return process
        except Exception as e:
            logging.error(f"Failed to start dashboard: {e}")
            return None

    def monitor_processes(self):
        """Monitor child processes and restart if needed"""
        while self.running:
            for name, process in list(self.processes.items()):
                if process.poll() is not None:  # Process has terminated
                    logging.warning(f"Process {name} terminated with code {process.returncode}")

                    # Restart the process
                    if name == 'recorder':
                        self.start_recorder()
                    elif name == 'processor':
                        self.start_processor()
                    elif name == 'detector':
                        self.start_detector()
                    elif name == 'dashboard':
                        self.start_dashboard()

            # Check thermal limits
            if not self.check_thermal_limit():
                logging.warning("Temperature limit exceeded, pausing operations")
                # Implement thermal management here
                time.sleep(30)  # Pause for 30 seconds before checking again
                continue

            # Check memory usage
            if not self.check_memory_usage():
                logging.warning("Memory limit exceeded, restarting supervisor...")
                self.restart_supervisor()
                break  # Break the loop as we're restarting

            # Refill token bucket for IO backpressure
            self.refill_token_bucket()

            time.sleep(5)  # Check every 5 seconds

    def restart_supervisor(self):
        """Restart the supervisor process"""
        logging.info("Restarting supervisor...")
        os.execv(sys.executable, ['python'] + sys.argv)

    def cleanup(self):
        """Clean up all processes before shutdown"""
        logging.info("Initiating cleanup...")

        for name, process in self.processes.items():
            try:
                if process.poll() is None:  # Process is still running
                    logging.info(f"Terminating {name} process (PID: {process.pid})")
                    process.terminate()
                    try:
                        process.wait(timeout=5)  # Wait up to 5 seconds
                    except subprocess.TimeoutExpired:
                        process.kill()  # Force kill if it doesn't terminate gracefully
                        logging.info(f"Force killed {name} process")
            except Exception as e:
                logging.error(f"Error terminating {name} process: {e}")

        logging.info("Cleanup completed")

    def run(self):
        """Main supervisor loop"""
        logging.info("Starting Voiseege Supervisor...")

        # Start all child processes
        self.start_recorder()
        self.start_processor()  # Added processor
        # Note: The detector is used internally by the processor, not as a separate process
        self.start_dashboard()

        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_processes)
        monitor_thread.daemon = True
        monitor_thread.start()

        # Main loop - keep running until shutdown signal
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt received")

        # Cleanup and exit
        self.cleanup()
        logging.info("Supervisor shutdown complete")


if __name__ == "__main__":
    supervisor = Supervisor()
    supervisor.run()