#!/usr/bin/env python3
"""
Detection Statistics Tracker
Tracks and summarizes all detections since system started
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import glob

class DetectionStats:
    def __init__(self, stats_file='detection_stats.json'):
        """Initialize detection statistics tracker"""
        self.stats_file = stats_file
        self.session_start = datetime.now()
        self.stats = {
            'session_start': self.session_start.isoformat(),
            'total_motion_events': 0,
            'total_detections': 0,
            'detections_by_type': {
                'person': 0,
                'dog': 0,
                'bird': 0
            },
            'bird_species': defaultdict(int),
            'confidence_stats': {
                'person': [],
                'dog': [],
                'bird': []
            },
            'hourly_stats': defaultdict(lambda: {'person': 0, 'dog': 0, 'bird': 0}),
            'daily_stats': defaultdict(lambda: {'person': 0, 'dog': 0, 'bird': 0}),
            'detection_log': []
        }
        self.load_stats()
    
    def load_stats(self):
        """Load existing statistics from file"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    saved_stats = json.load(f)
                
                # Merge with current session
                if 'detections_by_type' in saved_stats:
                    for obj_type, count in saved_stats['detections_by_type'].items():
                        self.stats['detections_by_type'][obj_type] = count
                
                if 'bird_species' in saved_stats:
                    self.stats['bird_species'].update(saved_stats['bird_species'])
                
                if 'total_motion_events' in saved_stats:
                    self.stats['total_motion_events'] = saved_stats['total_motion_events']
                
                if 'total_detections' in saved_stats:
                    self.stats['total_detections'] = saved_stats['total_detections']
                
                print(f"Loaded existing stats: {self.stats['total_detections']} total detections")
                
            except Exception as e:
                print(f"Could not load existing stats: {e}")
    
    def save_stats(self):
        """Save statistics to file"""
        try:
            # Convert defaultdicts to regular dicts for JSON serialization
            stats_to_save = {
                'session_start': self.stats['session_start'],
                'last_updated': datetime.now().isoformat(),
                'total_motion_events': self.stats['total_motion_events'],
                'total_detections': self.stats['total_detections'],
                'detections_by_type': dict(self.stats['detections_by_type']),
                'bird_species': dict(self.stats['bird_species']),
                'confidence_stats': self.stats['confidence_stats'],
                'hourly_stats': {k: dict(v) for k, v in self.stats['hourly_stats'].items()},
                'daily_stats': {k: dict(v) for k, v in self.stats['daily_stats'].items()},
                'detection_log': self.stats['detection_log'][-100:]  # Keep last 100 events
            }
            
            with open(self.stats_file, 'w') as f:
                json.dump(stats_to_save, f, indent=2)
                
        except Exception as e:
            print(f"Error saving stats: {e}")
    
    def record_motion_event(self):
        """Record a motion detection event"""
        self.stats['total_motion_events'] += 1
        self.save_stats()
    
    def record_detection(self, detections):
        """Record detection results"""
        timestamp = datetime.now()
        
        # Count detections
        for detection in detections['detections']:
            obj_type = detection['class']
            confidence = detection['confidence']
            
            # Update counters
            self.stats['detections_by_type'][obj_type] += 1
            self.stats['total_detections'] += 1
            
            # Track confidence
            self.stats['confidence_stats'][obj_type].append(confidence)
            
            # Track hourly stats
            hour_key = timestamp.strftime('%Y-%m-%d_%H')
            self.stats['hourly_stats'][hour_key][obj_type] += 1
            
            # Track daily stats
            day_key = timestamp.strftime('%Y-%m-%d')
            self.stats['daily_stats'][day_key][obj_type] += 1
            
            # Track bird species
            if obj_type == 'bird' and 'species' in detection:
                species = detection['species']
                self.stats['bird_species'][species] += 1
            
            # Add to detection log
            log_entry = {
                'timestamp': timestamp.isoformat(),
                'type': obj_type,
                'confidence': confidence
            }
            if 'species' in detection:
                log_entry['species'] = detection['species']
            
            self.stats['detection_log'].append(log_entry)
        
        self.save_stats()
    
    def get_session_summary(self):
        """Get summary for current session"""
        session_duration = datetime.now() - self.session_start
        
        summary = {
            'session_duration': str(session_duration).split('.')[0],  # Remove microseconds
            'session_start': self.session_start.strftime('%Y-%m-%d %H:%M:%S'),
            'motion_events': self.stats['total_motion_events'],
            'total_detections': self.stats['total_detections'],
            'detections': dict(self.stats['detections_by_type']),
            'bird_species': dict(self.stats['bird_species'])
        }
        
        return summary
    
    def get_confidence_averages(self):
        """Get average confidence scores for each object type"""
        averages = {}
        for obj_type, confidences in self.stats['confidence_stats'].items():
            if confidences:
                averages[obj_type] = {
                    'average': sum(confidences) / len(confidences),
                    'count': len(confidences),
                    'min': min(confidences),
                    'max': max(confidences)
                }
            else:
                averages[obj_type] = {'average': 0, 'count': 0, 'min': 0, 'max': 0}
        
        return averages
    
    def get_hourly_breakdown(self, hours=24):
        """Get detection breakdown for last N hours"""
        breakdown = {}
        now = datetime.now()
        
        for i in range(hours):
            hour_time = now - timedelta(hours=i)
            hour_key = hour_time.strftime('%Y-%m-%d_%H')
            hour_label = hour_time.strftime('%H:00')
            
            if hour_key in self.stats['hourly_stats']:
                breakdown[hour_label] = dict(self.stats['hourly_stats'][hour_key])
            else:
                breakdown[hour_label] = {'person': 0, 'dog': 0, 'bird': 0}
        
        return breakdown
    
    def get_daily_breakdown(self, days=7):
        """Get detection breakdown for last N days"""
        breakdown = {}
        now = datetime.now()
        
        for i in range(days):
            day_time = now - timedelta(days=i)
            day_key = day_time.strftime('%Y-%m-%d')
            day_label = day_time.strftime('%m-%d')
            
            if day_key in self.stats['daily_stats']:
                breakdown[day_label] = dict(self.stats['daily_stats'][day_key])
            else:
                breakdown[day_label] = {'person': 0, 'dog': 0, 'bird': 0}
        
        return breakdown
    
    def print_summary(self):
        """Print a formatted summary"""
        print("\n" + "="*60)
        print("🤖 AI MONITORING SYSTEM - DETECTION SUMMARY")
        print("="*60)
        
        # Session info
        summary = self.get_session_summary()
        print(f"📅 Session started: {summary['session_start']}")
        print(f"⏱️  Running for: {summary['session_duration']}")
        print(f"👁️  Motion events: {summary['motion_events']}")
        print(f"🎯 Total detections: {summary['total_detections']}")
        
        print("\n📊 DETECTION COUNTS:")
        print(f"   👤 Persons: {summary['detections']['person']}")
        print(f"   🐕 Dogs: {summary['detections']['dog']}")
        print(f"   🐦 Birds: {summary['detections']['bird']}")
        
        # Bird species breakdown
        if summary['bird_species']:
            print("\n🐦 BIRD SPECIES DETECTED:")
            for species, count in sorted(summary['bird_species'].items(), key=lambda x: x[1], reverse=True):
                print(f"   • {species}: {count}")
        
        # Confidence averages
        print("\n📈 CONFIDENCE AVERAGES:")
        averages = self.get_confidence_averages()
        for obj_type, stats in averages.items():
            if stats['count'] > 0:
                print(f"   {obj_type.capitalize()}: {stats['average']:.2f} (min: {stats['min']:.2f}, max: {stats['max']:.2f}, count: {stats['count']})")
        
        # Recent activity
        print("\n🕐 RECENT ACTIVITY (Last 12 hours):")
        hourly = self.get_hourly_breakdown(12)
        # get_hourly_breakdown returns hours in reverse chronological order
        # (current hour first).  Sorting them alphabetically breaks this
        # ordering around midnight because "23:00" would come before
        # "02:00".  Iterate over the existing order instead.
        for hour, counts in list(hourly.items())[:6]:
            total = sum(counts.values())
            if total > 0:
                print(f"   {hour}: {counts['person']}P, {counts['dog']}D, {counts['bird']}B")
        
        print("="*60)
    
    def print_live_stats(self):
        """Print a compact live statistics line"""
        summary = self.get_session_summary()
        duration_parts = summary['session_duration'].split(':')
        duration_str = f"{duration_parts[0]}h {duration_parts[1]}m"
        
        print(f"📊 Running {duration_str} | Motion: {summary['motion_events']} | "
              f"👤{summary['detections']['person']} 🐕{summary['detections']['dog']} 🐦{summary['detections']['bird']} | "
              f"Total: {summary['total_detections']}")

def analyze_existing_detections():
    """Analyze existing detection files to build historical stats"""
    print("🔍 Analyzing existing detection files...")
    
    stats = DetectionStats()
    detection_files = glob.glob("detections/detection_*.json")
    
    if not detection_files:
        print("No existing detection files found.")
        return stats
    
    print(f"Found {len(detection_files)} detection files to analyze...")
    
    for file_path in detection_files:
        try:
            with open(file_path, 'r') as f:
                detection_data = json.load(f)
            
            # Simulate recording this detection
            if 'detections' in detection_data:
                stats.record_detection(detection_data)
        
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    print(f"✅ Analysis complete. Found {stats.stats['total_detections']} total detections.")
    return stats

def main():
    """Main function for running statistics analysis"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'analyze':
        # Analyze existing files
        stats = analyze_existing_detections()
        stats.print_summary()
    else:
        # Show current stats
        stats = DetectionStats()
        stats.print_summary()

if __name__ == "__main__":
    main()
