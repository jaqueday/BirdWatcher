#!/usr/bin/env python3
"""Test script to verify all components work together"""

def test_all_components():
    print("🧪 TESTING ALL COMPONENTS")
    print("="*35)
    
    tests_passed = 0
    total_tests = 5
    
    # Test 1: NumPy
    try:
        import numpy as np
        version = np.__version__
        if version.startswith('1.'):
            print(f"✅ NumPy {version} (compatible)")
            tests_passed += 1
        else:
            print(f"❌ NumPy {version} (incompatible - should be 1.x)")
    except ImportError as e:
        print(f"❌ NumPy import failed: {e}")
    
    # Test 2: OpenCV
    try:
        import cv2
        print(f"✅ OpenCV {cv2.__version__}")
        tests_passed += 1
    except ImportError as e:
        print(f"❌ OpenCV import failed: {e}")
    
    # Test 3: Camera
    try:
        from picamera2 import Picamera2
        print("✅ Picamera2 available")
        tests_passed += 1
    except ImportError as e:
        print(f"❌ Picamera2 import failed: {e}")
    
    # Test 4: YOLO
    try:
        from ultralytics import YOLO
        print("✅ YOLO8 available")
        tests_passed += 1
    except ImportError as e:
        print(f"❌ YOLO8 import failed: {e}")
    
    # Test 5: Simple detection test
    try:
        model = YOLO('yolov8n.pt')
        print("✅ YOLO8 model loads")
        tests_passed += 1
    except Exception as e:
        print(f"❌ YOLO8 model test failed: {e}")
    
    print(f"\n📊 RESULTS: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All components working! System ready.")
        return True
    elif tests_passed >= 3:
        print("⚠️  Some components failed but core system should work")
        return True
    else:
        print("❌ Major issues - system needs fixing")
        return False

if __name__ == "__main__":
    test_all_components()
