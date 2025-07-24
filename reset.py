#!/usr/bin/env python3
"""
Quick Motion Detection Reset & Test
Resets background subtractor and tests with very sensitive settings
"""

import cv2
import numpy as np
import time
import os
import sys
from datetime import datetime

try:
    from picamera2 import Picamera2
except ImportError as e:
    print(f"❌ Picamera2 not available: {e}")
    sys.exit(1)

def reset_and_test_motion():
    """Reset motion detection and test with sensitive settings"""
    print("🔧 MOTION DETECTION RESET & TEST")
    print("="*50)
    
    # Kill any existing camera processes
    print("🔄 Resetting camera processes...")
    os.system("sudo pkill -f 'python.*main_monitor' >/dev/null 2>&1")
    os.system("sudo pkill -f 'picamera' >/dev/null 2>&1")
    time.sleep(2)
    
    print("📷 Initializing camera...")
    camera = Picamera2()
    
    # Use simple, reliable configuration
    config = camera.create_preview_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
    
    camera.configure(config)
    camera.start()
    time.sleep(3)  # Longer warm-up time
    
    print("🎯 Starting motion detection test...")
    print("   MOVE AROUND in front of the camera!")
    print("   Press Ctrl+C to stop")
    print("")
    
    # Create multiple background subtractors for comparison
    bg_subtractor1 = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
    bg_subtractor2 = cv2.createBackgroundSubtractorKNN(detectShadows=True)
    
    # Very sensitive settings
    min_area = 500  # Much smaller than default 5000
    sensitivity_threshold = 30  # Lower threshold
    
    frame_count = 0
    motion_detected_count = 0
    last_motion_time = 0
    
    try:
        while True:
            # Capture frame
            frame = camera.capture_array()
            frame_count += 1
            
            # Convert to BGR for OpenCV
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            else:
                bgr_frame = frame
            
            # Convert to grayscale and blur
            gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            
            # Try both background subtractors
            fg_mask1 = bg_subtractor1.apply(gray)
            fg_mask2 = bg_subtractor2.apply(gray)
            
            # Find contours in both masks
            contours1, _ = cv2.findContours(fg_mask1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours2, _ = cv2.findContours(fg_mask2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Check for motion with very sensitive settings
            motion_detected = False
            largest_area = 0
            motion_method = ""
            
            # Check MOG2 results
            for contour in contours1:
                area = cv2.contourArea(contour)
                if area > largest_area:
                    largest_area = area
                if area > min_area:
                    motion_detected = True
                    motion_method = "MOG2"
                    break
            
            # Check KNN results if MOG2 didn't detect
            if not motion_detected:
                for contour in contours2:
                    area = cv2.contourArea(contour)
                    if area > largest_area:
                        largest_area = area
                    if area > min_area:
                        motion_detected = True
                        motion_method = "KNN"
                        break
            
            # Log motion detection
            current_time = time.time()
            if motion_detected:
                motion_detected_count += 1
                last_motion_time = current_time
                print(f"🎯 MOTION #{motion_detected_count} detected using {motion_method}! Area: {largest_area:.0f}")
                
                # Save frame when motion detected
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                cv2.imwrite(f"test_motion_detection_{timestamp}.jpg", bgr_frame)
                
            # Show status every 30 frames (about every 3 seconds)
            elif frame_count % 30 == 0:
                time_since_motion = current_time - last_motion_time if last_motion_time > 0 else float('inf')
                print(f"📊 Frame {frame_count}: No motion (largest area: {largest_area:.0f}, "
                      f"last motion: {time_since_motion:.1f}s ago)")
            
            # Show periodic summary
            if frame_count % 100 == 0:
                print(f"📈 Summary after {frame_count} frames: {motion_detected_count} motion events detected")
            
            time.sleep(0.1)  # 10 FPS
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Test stopped by user")
    
    finally:
        camera.stop()
        
        print(f"\n📊 FINAL RESULTS:")
        print(f"   Total frames processed: {frame_count}")
        print(f"   Motion events detected: {motion_detected_count}")
        print(f"   Detection rate: {(motion_detected_count/frame_count)*100:.1f}%")
        
        if motion_detected_count == 0:
            print(f"\n❌ NO MOTION DETECTED!")
            print(f"   Possible issues:")
            print(f"   - Camera view is static (no movement)")
            print(f"   - Lighting is too dim or too bright")
            print(f"   - Camera lens is dirty or blocked")
            print(f"   - Background subtractor needs more time to adapt")
            print(f"\n🔧 Try:")
            print(f"   - Wave your arms dramatically")
            print(f"   - Turn lights on/off")
            print(f"   - Check camera lens")
            print(f"   - Run test longer (2-3 minutes)")
        else:
            print(f"\n✅ MOTION DETECTION IS WORKING!")
            print(f"   Check the saved test images: test_motion_detection_*.jpg")
            
        return motion_detected_count > 0

def create_ultra_sensitive_config():
    """Create config with ultra-sensitive motion detection"""
    config = {
        "motion_sensitivity": 1,      # Ultra sensitive
        "motion_min_area": 100,       # Very small area
        "motion_cooldown": 0.5,       # Very short cooldown
        "ai_confidence_threshold": 0.1,
        "save_all_detections": True,
        "verbose_motion": True,
        "quiet_mode": False,
        "log_level": "DEBUG"
    }
    
    with open('config_ultra_sensitive.json', 'w') as f:
        import json
        json.dump(config, f, indent=2)
    
    print("✅ Created config_ultra_sensitive.json")
    return config

def main():
    print("This will test motion detection with very sensitive settings")
    print("Make sure no other camera applications are running!")
    print("")
    
    input("Press Enter to start the test...")
    
    # Create ultra-sensitive config
    create_ultra_sensitive_config()
    
    # Run the motion test
    motion_working = reset_and_test_motion()
    
    print(f"\n" + "="*50)
    if motion_working:
        print("✅ MOTION DETECTION IS WORKING!")
        print("")
        print("Next step: Run your main monitoring system:")
        print("   python3 main_monitor_with_stats.py config_ultra_sensitive.json")
    else:
        print("❌ MOTION DETECTION NOT WORKING")
        print("")
        print("Troubleshooting steps:")
        print("1. Check camera physically (lens, connections)")
        print("2. Try running in brighter lighting")
        print("3. Reboot the Pi: sudo reboot")
        print("4. Check system logs: dmesg | grep -i camera")
    
    print("="*50)

if __name__ == "__main__":
    main()