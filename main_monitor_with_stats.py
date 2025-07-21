#!/usr/bin/env python3
"""
AI Monitoring System with Statistics Tracking
Tracks detections and provides summaries with reduced output
"""

import os
import sys
import signal
import time
import json
from datetime import datetime
import logging

# Import our custom modules
from camera_handler import MotionDetector
from ai_detector_simple import SimpleAIDetector
from detection_stats import DetectionStats

class MonitoringSystemWithStats:
    def __init__(self, config_file='config.json'):
        """Initialize the monitoring system with statistics"""
        self.motion_detector = None
        self.ai_detector = None
        self.stats_tracker = None
        self.running = False
        self.config = self.load_config(config_file)
        self.setup_logging()
        self.last_stats_time = 0
        self.last_detection_log_time = 0
        self.detection_log_interval = 30  # Only log detections every 30 seconds
        
    def load_config(self, config_file):
        """Load configuration from JSON file"""
        default_config = {
            "motion_sensitivity": 25,
            "motion_min_area": 5000,
            "motion_cooldown": 2,
            "ai_confidence_threshold": 0.3,
            "save_all_detections": True,
            "save_only_targets": False,
            "log_level": "INFO",
            "show_live_stats": False,  # Changed default to False for quieter operation
            "stats_interval": 300,  # Increased to 5 minutes for less frequent stats
            "verbose_motion": False,  # New: Control motion event logging
            "log_only_targets": True,  # New: Only log when targets are detected
            "quiet_mode": True  # New: Enable quiet operation
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
        else:
            # Create default config file
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Created default config file: {config_file}")
            
        return default_config
    
    def setup_logging(self):
        """Setup logging system"""
        log_level = getattr(logging, self.config['log_level'].upper())
        
        # Create custom formatter
        if self.config.get('quiet_mode', True):
            # Simpler format for quiet mode
            formatter = logging.Formatter('%(asctime)s - %(message)s')
        else:
            # Detailed format for verbose mode
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # File handler (always detailed)
        file_handler = logging.FileHandler('monitoring.log')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # Console handler (respects quiet mode)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        
        # Set up logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        self.logger.addHandler(file_handler)
        
        # Only add console handler if not in quiet mode or for important messages
        if not self.config.get('quiet_mode', True):
            self.logger.addHandler(console_handler)
        else:
            # In quiet mode, only show WARNING and above to console
            console_handler.setLevel(logging.WARNING)
            self.logger.addHandler(console_handler)
    
    def initialize(self):
        """Initialize all components"""
        print("Initializing AI Monitoring System...")  # Always show initialization
        
        # Create necessary directories
        os.makedirs("captures", exist_ok=True)
        os.makedirs("detections", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        
        # Initialize statistics tracker
        self.stats_tracker = DetectionStats()
        
        # Initialize motion detector with verbose setting
        self.motion_detector = MotionDetector(
            sensitivity=self.config['motion_sensitivity'],
            min_area=self.config['motion_min_area'],
            verbose=self.config.get('verbose_motion', False)  # Pass verbose setting
        )
        self.motion_detector.motion_cooldown = self.config['motion_cooldown']
        self.motion_detector.set_motion_callback(self.on_motion_detected)
        
        # Initialize AI detector
        self.ai_detector = SimpleAIDetector()
        if not self.ai_detector.initialize_models():
            print("Failed to initialize AI models")  # Always show critical errors
            return False
        
        # Show initial statistics only if not in quiet mode
        if not self.config.get('quiet_mode', True):
            self.stats_tracker.print_summary()
        
        print("System initialized successfully")  # Always show success
        return True
    
    def on_motion_detected(self, image):
        """Callback function called when motion is detected"""
        try:
            # Record motion event (silent)
            self.stats_tracker.record_motion_event()
            
            # Only log processing message in verbose mode
            if self.config.get('verbose_motion', False):
                self.logger.info("Processing motion detection...")
            
            # Run AI detection
            detections = self.ai_detector.detect_objects(image)
            
            # Record detection results (silent)
            if detections['detections']:
                self.stats_tracker.record_detection(detections)
            
            # Log detection results based on config
            self.log_detection_results(detections)
            
            # Save results if configured to do so
            if self.should_save_detection(detections):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"detections/detection_{timestamp}"
                self.ai_detector.save_detection_result(image, detections, filename)
            
            # Show live stats only if enabled (default off)
            if self.config.get('show_live_stats', False):
                self.stats_tracker.print_live_stats()
                
        except Exception as e:
            # Always show errors
            print(f"Error processing motion detection: {e}")
    
    def should_save_detection(self, detections):
        """Determine if detection should be saved based on config"""
        if self.config['save_all_detections']:
            return True
        
        if self.config['save_only_targets']:
            return (detections['has_person'] or 
                   detections['has_dog'] or 
                   detections['has_bird'])
        
        return False
    
    def log_detection_results(self, detections):
        """Log detection results with reduced frequency"""
        timestamp = detections['timestamp']
        current_time = time.time()
        
        # In quiet mode, only log targets and respect interval
        if self.config.get('quiet_mode', True):
            # Only log if there are target detections
            if not detections['detections']:
                return
            
            # Check if we should log based on target detection setting
            if self.config.get('log_only_targets', True):
                has_targets = (detections['has_person'] or 
                             detections['has_dog'] or 
                             detections['has_bird'])
                if not has_targets:
                    return
            
            # Respect logging interval to reduce spam
            if current_time - self.last_detection_log_time < self.detection_log_interval:
                return
            
            self.last_detection_log_time = current_time
        
        # Log summary
        if not detections['detections']:
            if self.config.get('verbose_motion', False):
                print(f"[{timestamp}] Motion detected - no targets found")
            return
        
        # Build summary
        summary = []
        if detections['has_person']:
            summary.append("Person")
        if detections['has_dog']:
            summary.append("Dog")
        if detections['has_bird']:
            summary.append(f"Bird ({detections['bird_species']})")
        
        if summary:  # Only log if there are targets
            print(f"[{timestamp}] 🎯 Detected: {', '.join(summary)}")
            
            # Log detailed results only in verbose mode
            if not self.config.get('quiet_mode', True):
                for detection in detections['detections']:
                    class_name = detection['class']
                    confidence = detection['confidence']
                    species_info = f" - Species: {detection['species']}" if 'species' in detection else ""
                    print(f"  - {class_name}: {confidence:.2f}{species_info}")
    
    def print_periodic_stats(self):
        """Print statistics periodically"""
        if time.time() - self.last_stats_time < self.config['stats_interval']:
            return
        
        self.last_stats_time = time.time()
        
        # Only show periodic stats if enabled
        if self.config.get('stats_interval', 0) > 0:
            print("\n" + "="*50)
            print("📊 PERIODIC STATISTICS UPDATE")
            print("="*50)
            self.stats_tracker.print_summary()
    
    def start(self):
        """Start the monitoring system"""
        if not self.initialize():
            print("Failed to initialize system")
            return False
        
        print("Starting motion monitoring...")
        
        # Start motion detection
        if not self.motion_detector.start_monitoring():
            print("Failed to start motion monitoring")
            return False
        
        self.running = True
        self.last_stats_time = time.time()
        
        # Show startup message based on mode
        if self.config.get('quiet_mode', True):
            print("🔍 AI Monitoring System running in QUIET mode")
            print("   - Only target detections will be shown")
            print("   - Send SIGUSR1 for stats (kill -USR1 <pid>)")
            print("   - Press Ctrl+C to stop")
        else:
            print("🔍 AI Monitoring System running in VERBOSE mode")
            print("   - All motion events will be logged")
            print("   - Commands available:")
            print("     - Ctrl+C: Stop system")
            print("     - Send SIGUSR1 for stats summary (kill -USR1 <pid>)")
        
        return True
    
    def stop(self):
        """Stop the monitoring system"""
        print("Stopping monitoring system...")
        self.running = False
        
        if self.motion_detector:
            self.motion_detector.stop_monitoring()
        
        # Final statistics summary
        if self.stats_tracker:
            print("\n" + "="*50)
            print("📊 FINAL SESSION SUMMARY")
            print("="*50)
            self.stats_tracker.print_summary()
        
        print("Monitoring system stopped")
    
    def signal_stats_handler(self, signum, frame):
        """Handle signal to show statistics"""
        print("\n" + "="*50)
        print("📊 STATISTICS ON DEMAND")
        print("="*50)
        self.stats_tracker.print_summary()
    
    def run(self):
        """Main run loop"""
        if not self.start():
            return
        
        # Set up signal handler for stats on demand
        signal.signal(signal.SIGUSR1, self.signal_stats_handler)
        
        try:
            while self.running:
                time.sleep(1)
                
                # Show periodic stats
                if self.config.get('stats_interval', 0) > 0:
                    self.print_periodic_stats()
                    
        except KeyboardInterrupt:
            print("\nReceived interrupt signal")
        finally:
            self.stop()

def signal_handler(sig, frame):
    """Handle system signals for graceful shutdown"""
    print("\nReceived shutdown signal. Stopping...")
    sys.exit(0)

def main():
    """Main function"""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == 'stats':
            # Just show current statistics
            stats = DetectionStats()
            stats.print_summary()
            return
        elif sys.argv[1] == 'analyze':
            # Analyze existing detection files
            from detection_stats import analyze_existing_detections
            stats = analyze_existing_detections()
            stats.print_summary()
            return
        elif sys.argv[1] == 'verbose':
            # Force verbose mode
            print("Running in VERBOSE mode (override)")
            monitor = MonitoringSystemWithStats()
            monitor.config['quiet_mode'] = False
            monitor.config['verbose_motion'] = True
            monitor.config['show_live_stats'] = True
            monitor.config['log_only_targets'] = False
            monitor.run()
            return
    
    # Create and run monitoring system
    monitor = MonitoringSystemWithStats()
    monitor.run()

if __name__ == "__main__":
    main()