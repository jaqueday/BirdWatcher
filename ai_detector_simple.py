import cv2
import numpy as np
from ultralytics import YOLO
from datetime import datetime
import json
import os

# TensorFlow Lite imports (much lighter for Raspberry Pi)
try:
    import tflite_runtime.interpreter as tflite
    print("✅ TensorFlow Lite runtime imported successfully")
    TFLITE_AVAILABLE = True
except ImportError:
    try:
        # Fallback to full TensorFlow Lite if tflite_runtime not available
        import tensorflow.lite as tflite
        print("✅ TensorFlow Lite imported successfully")
        TFLITE_AVAILABLE = True
    except ImportError as e:
        print(f"❌ TensorFlow Lite import failed: {e}")
        print("To install TensorFlow Lite runtime:")
        print("pip3 install tflite-runtime")
        TFLITE_AVAILABLE = False

class SimpleAIDetector:
    def __init__(self, models_dir='models'):
        """Initialize AI detector with YOLO + TensorFlow Lite dog classifier"""
        self.yolo_model = None
        self.dog_classifier = None
        self.models_dir = models_dir
        
        # Load custom dog class names
        self.dog_classes = self.load_dog_classes()
        
        # YOLO target classes (for initial detection)
        self.target_classes = {
            'person': 0,
            'dog': 16,    # Generic dog detection with YOLO
            'bird': 14
        }
        
        # Enhanced bird species classification
        self.bird_species_rules = {
            'large_dark': ['Crow', 'Raven', 'Blackbird'],
            'large_brown': ['Hawk', 'Eagle', 'Owl'],
            'medium_red': ['Cardinal', 'Robin'],
            'medium_blue': ['Blue Jay', 'Bluebird'],
            'medium_brown': ['Sparrow', 'Finch'],
            'small_any': ['Wren', 'Chickadee', 'Nuthatch'],
            'unknown': ['Unknown Bird']
        }
        
    def load_dog_classes(self):
        """Load custom dog class names from JSON file"""
        class_names_file = os.path.join(self.models_dir, 'class_names.json')
        try:
            if os.path.exists(class_names_file):
                with open(class_names_file, 'r') as f:
                    classes = json.load(f)
                print(f"✅ Loaded custom dog classes: {classes}")
                return classes
            else:
                print(f"❌ Class names file {class_names_file} not found")
                return ["felix", "leia"]  # fallback
        except Exception as e:
            print(f"❌ Error loading dog class names: {e}")
            return ["felix", "leia"]  # fallback
        
    def initialize_models(self):
        """Initialize YOLO for general detection + TensorFlow Lite for dog classification"""
        success = True
        
        # 1. Initialize YOLO for general object detection
        try:
            print("Loading YOLO8 model for general object detection...")
            self.yolo_model = YOLO('yolov8n.pt')
            print("✅ YOLO8 model loaded successfully")
        except Exception as e:
            print(f"❌ Failed to initialize YOLO8: {e}")
            success = False
        
        # 2. Initialize TensorFlow Lite dog classifier
        if TFLITE_AVAILABLE:
            if self.load_tflite_dog_classifier():
                print("✅ Using enhanced rule-based bird classification + TensorFlow Lite dog classification")
            else:
                print("⚠️  TensorFlow Lite dog classifier failed - using generic dog detection")
        else:
            print("⚠️  TensorFlow Lite not available - using generic dog detection")
            print("To install: pip3 install tflite-runtime")
        
        return success
    
    def load_tflite_dog_classifier(self):
        """Load the TensorFlow Lite dog classification model"""
        # Try TFLite files in order of preference
        tflite_files = [
            'dog_classifier_compatible.tflite',
            'dog_classifier.tflite'
        ]
        
        for model_file in tflite_files:
            model_path = os.path.join(self.models_dir, model_file)
            
            if not os.path.exists(model_path):
                print(f"⚠️  TFLite model not found: {model_path}")
                continue
                
            try:
                print(f"Loading TensorFlow Lite dog classifier: {model_file}")
                
                # Initialize TFLite interpreter
                self.dog_classifier = tflite.Interpreter(model_path=model_path)
                self.dog_classifier.allocate_tensors()
                
                # Get input and output details
                self.input_details = self.dog_classifier.get_input_details()
                self.output_details = self.dog_classifier.get_output_details()
                
                # Print model info
                input_shape = self.input_details[0]['shape']
                print(f"✅ TFLite dog classifier loaded successfully!")
                print(f"   Model: {model_file}")
                print(f"   Input shape: {input_shape}")
                print(f"   Classes: {self.dog_classes}")
                
                return True
                    
            except Exception as e:
                print(f"❌ Failed to load {model_file}: {e}")
                continue
        
        print("❌ No compatible TFLite dog classifier found")
        print(f"Available files in {self.models_dir}:")
        try:
            for file in os.listdir(self.models_dir):
                print(f"   - {file}")
        except:
            print(f"   Could not list directory {self.models_dir}")
        
        return False
    
    def classify_dog(self, dog_image):
        """
        Classify a detected dog using TensorFlow Lite
        
        Args:
            dog_image: Cropped image of the detected dog (RGB format)
            
        Returns:
            dict: Classification results with confidence scores
        """
        if self.dog_classifier is None:
            return {
                'predicted_class': 'Unknown Dog',
                'confidence': 0.0,
                'all_predictions': {}
            }
        
        try:
            # Preprocess the image for TFLite model
            processed_image = self.preprocess_dog_image(dog_image)
            
            # Run TFLite inference
            self.dog_classifier.set_tensor(self.input_details[0]['index'], processed_image)
            self.dog_classifier.invoke()
            predictions = self.dog_classifier.get_tensor(self.output_details[0]['index'])[0]
            
            # Get the predicted class
            predicted_class_idx = np.argmax(predictions)
            confidence = float(predictions[predicted_class_idx])
            
            # Get class name
            if predicted_class_idx < len(self.dog_classes):
                predicted_class = self.dog_classes[predicted_class_idx].capitalize()
            else:
                predicted_class = f"Dog_Class_{predicted_class_idx}"
            
            # Create all predictions dict
            all_predictions = {}
            for i, class_name in enumerate(self.dog_classes):
                if i < len(predictions):
                    all_predictions[class_name.capitalize()] = float(predictions[i])
            
            return {
                'predicted_class': predicted_class,
                'confidence': confidence,
                'all_predictions': all_predictions
            }
            
        except Exception as e:
            print(f"❌ Error in TFLite dog classification: {e}")
            return {
                'predicted_class': 'Classification Error',
                'confidence': 0.0,
                'all_predictions': {}
            }
    
    def preprocess_dog_image(self, image):
        """
        Preprocess dog image for TensorFlow Lite model
        """
        try:
            # Get input shape from the model
            input_shape = self.input_details[0]['shape']
            
            # Extract height and width (assuming NHWC format: [batch, height, width, channels])
            if len(input_shape) == 4:
                _, height, width, channels = input_shape
            else:
                # Default to common size if shape is unclear
                height, width, channels = 224, 224, 3
            
            target_size = (width, height)
            
            # Ensure image is RGB
            if len(image.shape) == 3 and image.shape[2] == 3:
                # Already RGB
                rgb_image = image
            elif len(image.shape) == 2:
                # Grayscale to RGB
                rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            else:
                # Handle other cases
                rgb_image = image[:, :, :3] if image.shape[2] > 3 else image
            
            # Resize to model's expected input size
            resized = cv2.resize(rgb_image, target_size)
            
            # Check if model expects float32 or uint8
            input_dtype = self.input_details[0]['dtype']
            
            if input_dtype == np.float32:
                # Normalize to [0, 1] for float32 models
                normalized = resized.astype(np.float32) / 255.0
            else:
                # Keep as uint8 for quantized models
                normalized = resized.astype(np.uint8)
            
            # Add batch dimension
            batched = np.expand_dims(normalized, axis=0)
            
            return batched
            
        except Exception as e:
            print(f"❌ Error preprocessing dog image: {e}")
            # Return a safe default
            try:
                input_shape = self.input_details[0]['shape']
                default_image = np.zeros(input_shape, dtype=self.input_details[0]['dtype'])
                return default_image
            except:
                # Final fallback
                return np.zeros((1, 224, 224, 3), dtype=np.float32)
    
    def _analyze_bird_features(self, bird_image, bbox_area):
        """Bird species classification (unchanged from original)"""
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
            hsv = cv2.cvtColor(bird_image, cv2.COLOR_BGR2HSV)
            h_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
            s_hist = cv2.calcHist([hsv], [1], None, [256], [0, 256])
            v_hist = cv2.calcHist([hsv], [2], None, [256], [0, 256])
            
            dominant_hue = np.argmax(h_hist)
            avg_saturation = np.average(np.arange(256), weights=s_hist.flatten())
            avg_brightness = np.average(np.arange(256), weights=v_hist.flatten())
            
            # Color classification
            if avg_brightness < 80:
                color_category = 'dark'
            elif dominant_hue < 15 or dominant_hue > 165:
                color_category = 'red'
            elif 90 < dominant_hue < 130:
                color_category = 'blue'
            elif avg_saturation < 100:
                color_category = 'brown'
            else:
                color_category = 'other'
            
            # Classify based on size and color
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
            else:
                return np.random.choice(self.bird_species_rules['small_any'])
                
        except Exception as e:
            print(f"Error in bird analysis: {e}")
            return "Unknown"
    
    def detect_objects(self, image):
        """
        Detect objects using YOLO, then classify dogs with TensorFlow Lite
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'detections': [],
            'has_person': False,
            'has_dog': False,
            'has_felix': False,
            'has_leia': False,
            'has_bird': False,
            'bird_species': None,
            'detected_dogs': [],
            'dog_classifications': []
        }
        
        try:
            # Run YOLO detection first
            yolo_results = self.yolo_model(image, conf=0.3, verbose=False)
            
            for result in yolo_results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        class_name = self.yolo_model.names[class_id]
                        
                        # Check if it's one of our target classes
                        if class_name in self.target_classes:
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            bbox_area = (x2 - x1) * (y2 - y1)
                            
                            detection = {
                                'class': class_name,
                                'confidence': confidence,
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'area': bbox_area
                            }
                            
                            # Special handling for dogs - run custom classification
                            if class_name == 'dog':
                                results['has_dog'] = True
                                
                                # Extract dog region and classify
                                dog_region = image[int(y1):int(y2), int(x1):int(x2)]
                                
                                if dog_region.size > 0:
                                    # Convert BGR to RGB for TensorFlow Lite
                                    dog_region_rgb = cv2.cvtColor(dog_region, cv2.COLOR_BGR2RGB)
                                    
                                    # Classify the dog with TFLite
                                    classification = self.classify_dog(dog_region_rgb)
                                    
                                    # Add classification info to detection
                                    detection['dog_classification'] = classification
                                    detection['dog_name'] = classification['predicted_class']
                                    detection['dog_confidence'] = classification['confidence']
                                    
                                    # Update results based on classification
                                    dog_name = classification['predicted_class'].lower()
                                    if 'felix' in dog_name:
                                        results['has_felix'] = True
                                        results['detected_dogs'].append('Felix')
                                    elif 'leia' in dog_name:
                                        results['has_leia'] = True
                                        results['detected_dogs'].append('Leia')
                                    else:
                                        results['detected_dogs'].append(classification['predicted_class'])
                                    
                                    results['dog_classifications'].append(classification)
                                else:
                                    # Fallback if dog region extraction fails
                                    detection['dog_name'] = 'Unknown Dog'
                                    detection['dog_confidence'] = 0.0
                                    results['detected_dogs'].append('Unknown Dog')
                            
                            elif class_name == 'person':
                                results['has_person'] = True
                            
                            elif class_name == 'bird':
                                results['has_bird'] = True
                                bird_region = image[int(y1):int(y2), int(x1):int(x2)]
                                species = self._analyze_bird_features(bird_region, bbox_area)
                                detection['species'] = species
                                results['bird_species'] = species
                            
                            results['detections'].append(detection)
            
            return results
            
        except Exception as e:
            print(f"❌ Error in object detection: {e}")
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
            
            # Special colors for specific dogs
            if 'dog_name' in detection:
                dog_name = detection['dog_name'].lower()
                if 'felix' in dog_name:
                    colors['dog'] = (255, 0, 255)  # Magenta for Felix
                elif 'leia' in dog_name:
                    colors['dog'] = (0, 255, 255)  # Cyan for Leia
            
            color = colors.get(class_name, (128, 128, 128))
            
            # Draw bounding box
            cv2.rectangle(output_image, (x1, y1), (x2, y2), color, 2)
            
            # Create label
            if class_name == 'dog' and 'dog_name' in detection:
                label = f"{detection['dog_name']}: {detection['dog_confidence']:.2f}"
            else:
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


# Test function to verify everything works
def test_detector():
    """Test the detector with a sample image"""
    print("🧪 Testing AI Detector...")
    
    detector = SimpleAIDetector()
    
    if detector.initialize_models():
        print("✅ All models initialized successfully!")
        
        # Create a test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[:] = (100, 150, 200)  # Fill with a color
        
        # Run detection
        results = detector.detect_objects(test_image)
        print(f"✅ Detection test completed: {len(results['detections'])} objects detected")
        
        return True
    else:
        print("❌ Model initialization failed")
        return False

if __name__ == "__main__":
    test_detector()