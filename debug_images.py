#!/usr/bin/env python3
"""
Debug script to check why dashboard isn't showing images
"""

import os
import json
import glob
from datetime import datetime

def debug_images():
    print("🔍 DEBUGGING DASHBOARD IMAGES")
    print("="*50)
    
    # Check directories
    captures_dir = "captures"
    detections_dir = "detections"
    
    print(f"📁 Checking directories...")
    print(f"   Captures dir exists: {os.path.exists(captures_dir)}")
    print(f"   Detections dir exists: {os.path.exists(detections_dir)}")
    
    if not os.path.exists(captures_dir):
        print("❌ captures/ directory missing!")
        return
    
    if not os.path.exists(detections_dir):
        print("❌ detections/ directory missing!")
        return
    
    # Count files
    capture_files = glob.glob(os.path.join(captures_dir, "motion_*.jpg"))
    detection_files = glob.glob(os.path.join(detections_dir, "detection_*.json"))
    
    print(f"\n📊 File counts:")
    print(f"   Capture images: {len(capture_files)}")
    print(f"   Detection files: {len(detection_files)}")
    
    if len(capture_files) == 0:
        print("❌ No capture images found!")
        print("   Expected files like: motion_20250723_120000.jpg")
        return
    
    if len(detection_files) == 0:
        print("❌ No detection files found!")
        print("   Expected files like: detection_20250723_120000.json")
        return
    
    # Check recent captures
    print(f"\n📷 Recent capture files:")
    recent_captures = sorted(capture_files, key=os.path.getmtime, reverse=True)[:5]
    for i, file_path in enumerate(recent_captures):
        filename = os.path.basename(file_path)
        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        print(f"   {i+1}. {filename} - {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check recent detections
    print(f"\n🎯 Recent detection files:")
    recent_detections = sorted(detection_files, key=os.path.getmtime, reverse=True)[:5]
    for i, file_path in enumerate(recent_detections):
        filename = os.path.basename(file_path)
        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        print(f"   {i+1}. {filename} - {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test the filtering logic
    print(f"\n🔍 Testing image filtering logic...")
    valid_images = []
    
    for file_path in recent_captures[:10]:  # Test first 10
        filename = os.path.basename(file_path)
        
        # Try to find corresponding detection file
        detection_file = file_path.replace('captures/', 'detections/').replace('.jpg', '.json')
        
        print(f"\n   Testing: {filename}")
        print(f"   Looking for: {os.path.basename(detection_file)}")
        print(f"   Detection file exists: {os.path.exists(detection_file)}")
        
        if os.path.exists(detection_file):
            try:
                with open(detection_file, 'r') as f:
                    detection_data = json.load(f)
                
                has_person = detection_data.get('has_person', False)
                has_dog = detection_data.get('has_dog', False)  
                has_bird = detection_data.get('has_bird', False)
                detections_list = detection_data.get('detections', [])
                
                print(f"   Has person: {has_person}")
                print(f"   Has dog: {has_dog}")
                print(f"   Has bird: {has_bird}")
                print(f"   Detection count: {len(detections_list)}")
                
                # Check if this would pass the filter
                if (has_person or has_dog or has_bird) and len(detections_list) > 0:
                    print(f"   ✅ WOULD SHOW (passes filter)")
                    valid_images.append(filename)
                else:
                    print(f"   ❌ FILTERED OUT (no valid detections)")
                    
            except Exception as e:
                print(f"   ❌ Error reading detection file: {e}")
        else:
            print(f"   ❌ No corresponding detection file")
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total captures: {len(capture_files)}")
    print(f"   Total detections: {len(detection_files)}")
    print(f"   Images that would show: {len(valid_images)}")
    
    if len(valid_images) == 0:
        print(f"\n❌ NO IMAGES PASS THE FILTER!")
        print(f"   This explains why dashboard shows no images")
        print(f"\n🔧 POSSIBLE FIXES:")
        print(f"   1. Check if your detection files have the right format")
        print(f"   2. Temporarily disable filtering to show all images")
        print(f"   3. Check if motion detection is actually finding objects")
    else:
        print(f"\n✅ Found {len(valid_images)} valid images")
        print(f"   Dashboard should show these images")
        print(f"   If not showing, check web server image serving")
    
    # Show sample detection file structure
    if len(recent_detections) > 0:
        print(f"\n📄 Sample detection file structure:")
        try:
            with open(recent_detections[0], 'r') as f:
                sample_data = json.load(f)
            
            print(f"   File: {os.path.basename(recent_detections[0])}")
            print(f"   Keys: {list(sample_data.keys())}")
            if 'detections' in sample_data:
                print(f"   Detection count: {len(sample_data['detections'])}")
                if sample_data['detections']:
                    print(f"   Sample detection: {sample_data['detections'][0]}")
        except Exception as e:
            print(f"   Error reading sample: {e}")

if __name__ == "__main__":
    debug_images()
