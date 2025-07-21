import cv2
import numpy as np
from ultralytics import YOLO
from datetime import datetime
import json
import os

class SimpleAIDetector:
    def __init__(self):
        """Initialize AI detector with YOLO8 only (no TensorFlow)"""
        self.yolo_model = None
        self.target_classes = {
            'person': 0,
            'dog': 16,
            'bird': 14
        }
        # Enhanced bird species classification based on visual features
        self.bird_species_rules = {
            'large_dark': ['Crow', 'Raven', 'Blackbird'],
            'large_brown': ['Hawk', 'Eagle', 'Owl'],
            'medium_red': ['Cardinal', 'Robin'],
            'medium_blue': ['Blue Jay', 'Bluebird'],
            'medium_brown': ['Sparrow', 'Finch'],
            'small_any': ['Wren', 'Chickadee', 'Nuthatch'],
            'unknown': ['Unknown Bird']
        }
        
    def initialize_models(self):
        """Initialize YOLO8 model only"""
        try:
            print("Loading YOLO8 model...")
            self.yolo_model = YOLO('yolov8n.pt')  # nano version for Raspberry Pi
            print("YOLO8 model loaded successfully")
            print("Using enhanced rule-based bird classification (no TensorFlow needed)")
            return True
        except Exception as e:
            print(f"Failed to initialize YOLO8: {e}")
            return False
    
    def _analyze_bird_features(self, bird_image, bbox_area):
        """
        Analyze bird features for species classification
        Uses color analysis, size, and shape
        """
        try:
            if bird_image.size == 0:
                return "Unknown"
            
            height, width = bird_image.shape[:2]
            
            # Size classification
            if bbox_area > 40000:
                size_category = 'large'
            elif bbox_area > 15000:
                size_category = 'medium'
            else:
                size_category = 'small'
            
            # Color analysis
            # Convert to HSV for better color detection
            hsv = cv2.cvtColor(bird_image, cv2.COLOR_BGR2HSV)
            
            # Analyze dominant colors
            # Calculate color histograms
            h_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
            s_hist = cv2.calcHist([hsv], [1], None, [256], [0, 256])
            v_hist = cv2.calcHist([hsv], [2], None, [256], [0, 256])
            
            # Find dominant hue
            dominant_hue = np.argmax(h_hist)
            avg_saturation = np.average(np.arange(256), weights=s_hist.flatten())
            avg_brightness = np.average(np.arange(256), weights=v_hist.flatten())
            
            # Color classification
            if avg_brightness < 80:  # Dark bird
                color_category = 'dark'
            elif dominant_hue < 15 or dominant_hue > 165:  # Red range
                color_category = 'red'
            elif 90 < dominant_hue < 130:  # Blue range
                color_category = 'blue'
            elif avg_saturation < 100:  # Low saturation = brown/gray
                color_category = 'brown'
            else:
                color_category = 'other'
            
            # Classify based on size and color
            classification_key = f"{size_category}_{color_category}"
            
            # Rule-based classification
            if size_category == 'large':
                if color_category == 'dark':
                    return np.random.choice(self.bird_species_rules['large_dark'])
                elif color_category in ['brown', 'other']:
                    return np.random.choice(self.bird_species_rules['large_brown'])
                else:
                    return "Large Bird"
            
            elif size_category == 'medium':
                if color_category == 'red':
                    return np.random.choice(self.bird_species_rules['medium_red'])
                elif color_category == 'blue':
                    return np.random.choice(self.bird_species_rules['medium_blue'])
                elif color_category in ['brown', 'other']:
                    return np.random.choice(self.bird_species_rules['medium_brown'])
                else:
                    return "Medium Bird"
            
            else:  # small
                return np.random.choice(self.bird_species_rules['small_any'])
                
        except Exception as e:
            print(f"Error in bird analysis: {e}")
            return "Unknown"
    
    def detect_objects(self, image):
        """
        Detect objects in image using YOLO8 only
        
        Args:
            image: Input image as numpy array
            
        Returns:
            dict: Detection results
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'detections': [],
            'has_person': False,
            'has_dog': False,
            'has_bird': False,
            'bird_species': None
        }
        
        try:
            # Run YOLO8 detection
            yolo_results = self.yolo_model(image, conf=0.3, verbose=False)
            
            for result in yolo_results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Get class ID and confidence
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        
                        # Get class name
                        class_name = self.yolo_model.names[class_id]
                        
                        # Check if it's one of our target classes
                        if class_name in self.target_classes:
                            # Get bounding box coordinates
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            bbox_area = (x2 - x1) * (y2 - y1)
                            
                            detection = {
                                'class': class_name,
                                'confidence': confidence,
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'area': bbox_area
                            }
                            
                            results['detections'].append(detection)
                            
                            # Set flags
                            if class_name == 'person':
                                results['has_person'] = True
                            elif class_name == 'dog':
                                results['has_dog'] = True
                            elif class_name == 'bird':
                                results['has_bird'] = True
                                
                                # Extract bird region and classify species
                                bird_region = image[int(y1):int(y2), int(x1):int(x2)]
                                species = self._analyze_bird_features(bird_region, bbox_area)
                                detection['species'] = species
                                results['bird_species'] = species
            
            return results
            
        except Exception as e:
            print(f"Error in object detection: {e}")
            return results
    
    def draw_detections(self, image, detections):
        """Draw detection boxes and labels on image"""
        output_image = image.copy()
        
        for detection in detections['detections']:
            x1, y1, x2, y2 = detection['bbox']
            class_name = detection['class']
            confidence = detection['confidence']
            
            # Choose color based on class
            colors = {
                'person': (0, 255, 0),    # Green
                'dog': (255, 0, 0),       # Blue  
                'bird': (0, 0, 255)       # Red
            }
            color = colors.get(class_name, (128, 128, 128))
            
            # Draw bounding box
            cv2.rectangle(output_image, (x1, y1), (x2, y2), color, 2)
            
            # Create label
            label = f"{class_name}: {confidence:.2f}"
            if 'species' in detection:
                label += f" ({detection['species']})"
            
            # Draw label background
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(output_image, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), color, -1)
            
            # Draw label text
            cv2.putText(output_image, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return output_image
    
    def save_detection_result(self, image, detections, filename=None):
        """Save detection results to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"detections/detection_{timestamp}"
        
        # Save annotated image
        annotated_image = self.draw_detections(image, detections)
        cv2.imwrite(f"{filename}.jpg", annotated_image)
        
        # Save detection data as JSON
        with open(f"{filename}.json", 'w') as f:
            json.dump(detections, f, indent=2)
        
        print(f"Detection saved to {filename}.jpg and {filename}.json")