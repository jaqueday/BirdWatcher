import time
import threading
from datetime import datetime
import os
import cv2
import numpy as np

# Import with error handling
try:
    from picamera2 import Picamera2
    print("Picamera2 imported successfully")
except ImportError as e:
    print(f"Picamera2 import failed: {e}")
    raise

class MotionDetector:
    def __init__(self, sensitivity=25, min_area=5000, verbose=False):
        """
        Initialize motion detector for Raspberry Pi Camera Module 3
        
        Args:
            sensitivity: Motion sensitivity (lower = more sensitive)
            min_area: Minimum area of motion to trigger detection
            verbose: Enable detailed logging (default: False for quiet operation)
        """
        self.sensitivity = sensitivity
        self.min_area = min_area
        self.verbose = verbose
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        self.camera = None
        self.running = False
        self.motion_callback = None
        self.last_motion_time = 0
        self.motion_cooldown = 2  # seconds between motion detections
        
    def initialize_camera(self):
        """Initialize the Raspberry Pi camera"""
        try:
            self.camera = Picamera2()
            
            # Configure camera for motion detection (using RGB, not RGBA)
            config = self.camera.create_preview_configuration(
                main={"size": (640, 480), "format": "RGB888"},  # Force RGB format
                lores={"size": (320, 240), "format": "YUV420"},
                display="lores"
            )
            self.camera.configure(config)
            self.camera.start()
            time.sleep(2)  # Let camera warm up
            if self.verbose:
                print("Camera initialized successfully with RGB format")
            return True
        except Exception as e:
            print(f"Failed to initialize camera: {e}")  # Always show errors
            return False
    
    def capture_high_res_image(self):
        """Capture a high-resolution image for AI analysis"""
        try:
            # Capture high-resolution image for AI processing
            # Switch to high-res temporarily
            self.camera.stop()
            
            high_res_config = self.camera.create_still_configuration(
                main={"size": (2304, 1296), "format": "RGB888"}  # Force RGB format
            )
            self.camera.configure(high_res_config)
            self.camera.start()
            time.sleep(0.5)  # Brief pause for configuration
            
            # Capture the image
            image = self.camera.capture_array()
            
            # Ensure it's 3-channel RGB
            if len(image.shape) == 3 and image.shape[2] == 4:
                # Convert RGBA to RGB if needed
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
            elif len(image.shape) == 3 and image.shape[2] == 3:
                # Already RGB, but might be BGR, convert to RGB for YOLO
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Save a copy of the captured image
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            cv2.imwrite(f"captures/motion_{timestamp}.jpg", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            
            # Switch back to motion detection mode
            self.camera.stop()
            motion_config = self.camera.create_preview_configuration(
                main={"size": (640, 480), "format": "RGB888"},
                lores={"size": (320, 240), "format": "YUV420"},
                display="lores"
            )
            self.camera.configure(motion_config)
            self.camera.start()
            time.sleep(0.5)  # Brief pause for configuration
            
            # Only print image info in verbose mode
            if self.verbose:
                print(f"Captured image shape: {image.shape}")
            return image
            
        except Exception as e:
            print(f"Failed to capture high-res image: {e}")  # Always show errors
            # Try to restart motion detection mode
            try:
                self.camera.stop()
                motion_config = self.camera.create_preview_configuration(
                    main={"size": (640, 480), "format": "RGB888"},
                    lores={"size": (320, 240), "format": "YUV420"},
                    display="lores"
                )
                self.camera.configure(motion_config)
                self.camera.start()
            except:
                pass
            return None
    
    def detect_motion(self, frame):
        """
        Detect motion in the current frame
        
        Args:
            frame: Current camera frame
            
        Returns:
            bool: True if motion detected, False otherwise
        """
        try:
            # Ensure frame is in correct format
            if len(frame.shape) == 3:
                if frame.shape[2] == 4:  # RGBA
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
                elif frame.shape[2] == 3:  # RGB
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            
            # Apply background subtraction
            fg_mask = self.background_subtractor.apply(gray)
            
            # Find contours
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Check if any contour is large enough to be considered motion
            for contour in contours:
                if cv2.contourArea(contour) > self.min_area:
                    return True
            
            return False
        except Exception as e:
            if self.verbose:  # Only show motion detection errors in verbose mode
                print(f"Error in motion detection: {e}")
            return False
    
    def set_motion_callback(self, callback):
        """Set callback function to be called when motion is detected"""
        self.motion_callback = callback
    
    def start_monitoring(self):
        """Start motion monitoring in a separate thread"""
        if not self.initialize_camera():
            return False
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        if self.verbose:
            print("Motion monitoring started")
        return True
    
    def stop_monitoring(self):
        """Stop motion monitoring"""
        self.running = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join()
        if self.camera:
            self.camera.stop()
        if self.verbose:
            print("Motion monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Capture frame for motion detection
                frame = self.camera.capture_array()
                
                # Check for motion
                if self.detect_motion(frame):
                    current_time = time.time()
                    
                    # Check cooldown period
                    if current_time - self.last_motion_time > self.motion_cooldown:
                        self.last_motion_time = current_time
                        
                        # Only print motion detection in verbose mode
                        if self.verbose:
                            print(f"Motion detected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # Capture high-resolution image
                        high_res_image = self.capture_high_res_image()
                        
                        # Call callback if set
                        if self.motion_callback and high_res_image is not None:
                            self.motion_callback(high_res_image)
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")  # Always show critical errors
                time.sleep(1)

# Create directories for storing captures
os.makedirs("captures", exist_ok=True)
os.makedirs("detections", exist_ok=True)