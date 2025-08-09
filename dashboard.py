#!/usr/bin/env python3
"""
Bird Watcher Web Dashboard
Enhanced version with separate motion/AI detection views and Felix/Leia tracking
"""

from flask import Flask, render_template, jsonify, send_from_directory
import os
import json
import glob
from datetime import datetime, timedelta
from detection_stats import DetectionStats

app = Flask(__name__)

# Configuration
CAPTURES_DIR = "captures"
DETECTIONS_DIR = "detections"
STATIC_DIR = "static"

# Create necessary directories
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs("templates", exist_ok=True)

class DashboardData:
    def __init__(self):
        self.stats = DetectionStats()
    
    def get_summary_data(self):
        """Get all data needed for dashboard"""
        summary = self.stats.get_session_summary()
        confidence_averages = self.stats.get_confidence_averages()
        hourly_breakdown = self.stats.get_hourly_breakdown(12)
        
        # Get recent motion captures and AI detections separately
        recent_motion_captures = self.get_recent_motion_captures(limit=3)
        recent_ai_detections = self.get_recent_ai_detections(limit=3)
        
        # Calculate some additional metrics
        total_detections = sum(summary['detections'].values())
        detection_rate = (total_detections / summary['motion_events'] * 100) if summary['motion_events'] > 0 else 0
        
        # Get specific dog counts
        felix_count, leia_count = self.get_dog_counts()
        
        return {
            'summary': summary,
            'confidence_averages': confidence_averages,
            'hourly_breakdown': hourly_breakdown,
            'recent_motion_captures': recent_motion_captures,
            'recent_ai_detections': recent_ai_detections,
            'total_detections': total_detections,
            'detection_rate': round(detection_rate, 1),
            'system_status': self.get_system_status(),
            'felix_count': felix_count,
            'leia_count': leia_count
        }
    
    def get_recent_motion_captures(self, limit=3):
        """Get recent motion capture files (just the motion events)"""
        capture_files = glob.glob(os.path.join(CAPTURES_DIR, "motion_*.jpg"))
        
        if not capture_files:
            return []
        
        # Sort by modification time (newest first)
        capture_files.sort(key=os.path.getmtime, reverse=True)
        
        recent = []
        for file_path in capture_files[:limit]:
            try:
                filename = os.path.basename(file_path)
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                recent.append({
                    'filename': filename,
                    'timestamp': mod_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'time_ago': self.time_ago(mod_time),
                    'type': 'motion'
                })
            except:
                continue
        
        return recent
    
    def get_recent_ai_detections(self, limit=3):
        """Get recent AI detection files (with bounding boxes)"""
        detection_files = glob.glob(os.path.join(DETECTIONS_DIR, "detection_*.jpg"))
        
        if not detection_files:
            return []
        
        # Sort by modification time (newest first)
        detection_files.sort(key=os.path.getmtime, reverse=True)
        
        recent = []
        for file_path in detection_files[:limit]:
            try:
                filename = os.path.basename(file_path)
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # Try to find corresponding JSON file with detection data
                json_file = file_path.replace('.jpg', '.json')
                detection_info = None
                
                if os.path.exists(json_file):
                    try:
                        with open(json_file, 'r') as f:
                            detection_data = json.load(f)
                            
                            # Build detection summary
                            detected_objects = []
                            if detection_data.get('has_person', False):
                                detected_objects.append('Person')
                            if detection_data.get('has_felix', False):
                                detected_objects.append('Felix')
                            elif detection_data.get('has_leia', False):
                                detected_objects.append('Leia')
                            elif detection_data.get('has_dog', False):
                                detected_objects.append('Dog')
                            if detection_data.get('has_bird', False):
                                bird_species = detection_data.get('bird_species', 'Bird')
                                detected_objects.append(bird_species)
                            
                            detection_info = {
                                'has_person': detection_data.get('has_person', False),
                                'has_dog': detection_data.get('has_dog', False),
                                'has_felix': detection_data.get('has_felix', False),
                                'has_leia': detection_data.get('has_leia', False),
                                'has_bird': detection_data.get('has_bird', False),
                                'bird_species': detection_data.get('bird_species', None),
                                'detection_count': len(detection_data.get('detections', [])),
                                'detected_objects': detected_objects,
                                'summary': ', '.join(detected_objects) if detected_objects else 'No objects'
                            }
                    except:
                        pass
                
                recent.append({
                    'filename': filename,
                    'timestamp': mod_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'time_ago': self.time_ago(mod_time),
                    'detection_info': detection_info,
                    'type': 'detection'
                })
            except:
                continue
        
        return recent
    
    def get_dog_counts(self):
        """Get specific counts for Felix and Leia"""
        felix_count = 0
        leia_count = 0
        
        # Check detection JSON files for Felix/Leia counts
        detection_files = glob.glob(os.path.join(DETECTIONS_DIR, "detection_*.json"))
        
        for json_file in detection_files:
            try:
                with open(json_file, 'r') as f:
                    detection_data = json.load(f)
                    
                if detection_data.get('has_felix', False):
                    felix_count += 1
                if detection_data.get('has_leia', False):
                    leia_count += 1
                    
            except:
                continue
        
        return felix_count, leia_count
    
    def get_system_status(self):
        """Get system status information"""
        # Check when last detection occurred
        capture_files = glob.glob(os.path.join(CAPTURES_DIR, "motion_*.jpg"))
        
        if capture_files:
            latest_file = max(capture_files, key=os.path.getmtime)
            last_activity = datetime.fromtimestamp(os.path.getmtime(latest_file))
            hours_since = (datetime.now() - last_activity).total_seconds() / 3600
            
            if hours_since < 1:
                status = "active"
                status_text = f"Last activity: {self.time_ago(last_activity)}"
            elif hours_since < 24:
                status = "recent"
                status_text = f"Last activity: {hours_since:.1f} hours ago"
            else:
                status = "idle"
                status_text = f"Last activity: {hours_since/24:.1f} days ago"
        else:
            status = "no_data"
            status_text = "No captures found"
        
        return {
            'status': status,
            'status_text': status_text,
            'total_captures': len(capture_files) if capture_files else 0
        }
    
    def time_ago(self, timestamp):
        """Convert timestamp to human-readable 'time ago' format"""
        now = datetime.now()
        diff = now - timestamp
        
        if diff.total_seconds() < 60:
            return "Just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes}m ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago"
        else:
            days = int(diff.total_seconds() / 86400)
            return f"{days}d ago"

# Initialize dashboard data
dashboard_data = DashboardData()

@app.route('/')
def index():
    """Main dashboard page"""
    data = dashboard_data.get_summary_data()
    return render_template('dashboard.html', **data)

@app.route('/api/stats')
def api_stats():
    """JSON API endpoint for live updates"""
    data = dashboard_data.get_summary_data()
    return jsonify(data)

@app.route('/captures/<filename>')
def serve_capture(filename):
    """Serve capture images"""
    return send_from_directory(CAPTURES_DIR, filename)

@app.route('/detections/<filename>')
def serve_detection(filename):
    """Serve detection images"""
    return send_from_directory(DETECTIONS_DIR, filename)

def create_html_template():
    """Create the HTML template file"""
    template_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🐦 Bird Watcher Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .status-active { background: #4ade80; color: #166534; }
        .status-recent { background: #fbbf24; color: #92400e; }
        .status-idle { background: #f87171; color: #991b1b; }
        .status-no_data { background: #6b7280; color: white; }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .card h2 {
            color: #4f46e5;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            text-align: center;
        }
        
        .stat-item {
            padding: 15px;
            background: #f8fafc;
            border-radius: 8px;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #4f46e5;
        }
        
        .stat-label {
            font-size: 0.9em;
            color: #64748b;
            margin-top: 5px;
        }
        
        .dog-stats {
            grid-column: 1 / -1;
        }
        
        .dog-stats .stats-grid {
            grid-template-columns: repeat(4, 1fr);
        }
        
        .felix-stat { background: #fef3ff; }
        .leia-stat { background: #f0f9ff; }
        
        .felix-stat .stat-number { color: #a855f7; }
        .leia-stat .stat-number { color: #0ea5e9; }
        
        .images-section {
            grid-column: 1 / -1;
        }
        
        .images-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        .image-group h3 {
            color: #4f46e5;
            margin-bottom: 15px;
            font-size: 1.1em;
            text-align: center;
        }
        
        .captures-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
        }
        
        .capture-item {
            background: #f8fafc;
            border-radius: 8px;
            overflow: hidden;
            text-align: center;
            transition: transform 0.2s;
        }
        
        .capture-item:hover {
            transform: scale(1.02);
        }
        
        .capture-item img {
            width: 100%;
            height: 140px;
            object-fit: cover;
            cursor: pointer;
        }
        
        .capture-info {
            padding: 10px;
        }
        
        .capture-time {
            font-size: 0.8em;
            color: #64748b;
            margin-bottom: 5px;
        }
        
        .detection-badges {
            display: flex;
            justify-content: center;
            gap: 5px;
            flex-wrap: wrap;
        }
        
        .detection-badge {
            font-size: 0.7em;
            padding: 2px 6px;
            border-radius: 10px;
            color: white;
        }
        
        .badge-person { background: #10b981; }
        .badge-dog { background: #f59e0b; }
        .badge-felix { background: #a855f7; }
        .badge-leia { background: #0ea5e9; }
        .badge-bird { background: #ef4444; }
        
        .detection-summary {
            font-size: 0.8em;
            color: #374151;
            margin-top: 5px;
            font-weight: 500;
        }
        
        .motion-indicator {
            background: #6b7280;
            color: white;
            font-size: 0.7em;
            padding: 2px 6px;
            border-radius: 10px;
        }
        
        .refresh-info {
            text-align: center;
            color: white;
            margin-top: 20px;
            opacity: 0.8;
        }
        
        @media (max-width: 1024px) {
            .images-container {
                grid-template-columns: 1fr;
                gap: 20px;
            }
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
            
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .dog-stats .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .header h1 {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐦 Bird Watcher Dashboard</h1>
            <p>Session running for {{ summary.session_duration }}</p>
            <span class="status-badge status-{{ system_status.status }}">
                {{ system_status.status_text }}
            </span>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>📊 Detection Summary</h2>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-number">{{ summary.detections.person }}</div>
                        <div class="stat-label">👤 People</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{{ summary.detections.dog }}</div>
                        <div class="stat-label">🐕 Dogs</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{{ summary.detections.bird }}</div>
                        <div class="stat-label">🐦 Birds</div>
                    </div>
                </div>
            </div>
            
            <div class="card dog-stats">
                <h2>🐕 Dog Detections</h2>
                <div class="stats-grid">
                    <div class="stat-item felix-stat">
                        <div class="stat-number">{{ felix_count }}</div>
                        <div class="stat-label">🐕 Felix</div>
                    </div>
                    <div class="stat-item leia-stat">
                        <div class="stat-number">{{ leia_count }}</div>
                        <div class="stat-label">🐕 Leia</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{{ summary.motion_events }}</div>
                        <div class="stat-label">Motion Events</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{{ detection_rate }}%</div>
                        <div class="stat-label">Detection Rate</div>
                    </div>
                </div>
            </div>
            
            {% if summary.bird_species %}
            <div class="card">
                <h2>🐦 Bird Species</h2>
                {% for species, count in summary.bird_species.items() %}
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span>{{ species }}</span>
                    <strong>{{ count }}</strong>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            <div class="card images-section">
                <h2>📷 Recent Activity</h2>
                <div class="images-container">
                    <div class="image-group">
                        <h3>🎬 Latest Motion Captures</h3>
                        {% if recent_motion_captures %}
                        <div class="captures-grid">
                            {% for capture in recent_motion_captures %}
                            <div class="capture-item">
                                <img src="/captures/{{ capture.filename }}" alt="Motion Capture" onclick="window.open(this.src, '_blank')">
                                <div class="capture-info">
                                    <div class="capture-time">{{ capture.time_ago }}</div>
                                    <div class="motion-indicator">Motion Event</div>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                        {% else %}
                        <p style="text-align: center; color: #6b7280;">No recent motion captures</p>
                        {% endif %}
                    </div>
                    
                    <div class="image-group">
                        <h3>🎯 Latest AI Detections</h3>
                        {% if recent_ai_detections %}
                        <div class="captures-grid">
                            {% for detection in recent_ai_detections %}
                            <div class="capture-item">
                                <img src="/detections/{{ detection.filename }}" alt="AI Detection" onclick="window.open(this.src, '_blank')">
                                <div class="capture-info">
                                    <div class="capture-time">{{ detection.time_ago }}</div>
                                    {% if detection.detection_info %}
                                    <div class="detection-badges">
                                        {% if detection.detection_info.has_person %}
                                        <span class="detection-badge badge-person">Person</span>
                                        {% endif %}
                                        {% if detection.detection_info.has_felix %}
                                        <span class="detection-badge badge-felix">Felix</span>
                                        {% elif detection.detection_info.has_leia %}
                                        <span class="detection-badge badge-leia">Leia</span>
                                        {% elif detection.detection_info.has_dog %}
                                        <span class="detection-badge badge-dog">Dog</span>
                                        {% endif %}
                                        {% if detection.detection_info.has_bird %}
                                        <span class="detection-badge badge-bird">
                                            {% if detection.detection_info.bird_species %}
                                                {{ detection.detection_info.bird_species }}
                                            {% else %}
                                                Bird
                                            {% endif %}
                                        </span>
                                        {% endif %}
                                    </div>
                                    <div class="detection-summary">{{ detection.detection_info.summary }}</div>
                                    {% else %}
                                    <div class="detection-summary">Processing...</div>
                                    {% endif %}
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                        {% else %}
                        <p style="text-align: center; color: #6b7280;">No recent AI detections</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
        
        <div class="refresh-info">
            <p>📱 Dashboard automatically refreshes every 30 seconds</p>
            <p>💡 Click on images to view full size</p>
            <p>🎯 AI detections show bounding boxes around detected objects</p>
        </div>
    </div>
    
    <script>
        // Auto-refresh every 30 seconds
        setInterval(function() {
            location.reload();
        }, 30000);
        
        // Show last updated time
        console.log('Dashboard loaded at:', new Date().toLocaleString());
    </script>
</body>
</html>'''
    
    with open('templates/dashboard.html', 'w') as f:
        f.write(template_content)

def main():
    """Main function to run the dashboard"""
    print("🚀 Setting up Bird Watcher Web Dashboard...")
    
    # Create template file
    create_html_template()
    print("✅ Created HTML template")
    
    # Check if required directories exist
    if not os.path.exists(CAPTURES_DIR):
        print(f"⚠️  Warning: {CAPTURES_DIR} directory not found")
        print("   Make sure your monitoring system is saving captures")
    
    if not os.path.exists(DETECTIONS_DIR):
        print(f"⚠️  Warning: {DETECTIONS_DIR} directory not found")
        print("   Detection images won't be available")
    
    # Get Pi's IP address for instructions
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "YOUR_PI_IP"
    
    print("\n" + "="*50)
    print("🎉 ENHANCED DASHBOARD READY!")
    print("="*50)
    print(f"📱 Access from any device on your WiFi:")
    print(f"   • On this Pi: http://localhost:5000")
    print(f"   • From phone/laptop: http://{local_ip}:5000")
    print("")
    print("🆕 New Features:")
    print("   • Separate Motion vs AI Detection images")
    print("   • Felix and Leia specific counters")
    print("   • Enhanced visual design")
    print("   • Mobile-responsive layout")
    print("")
    print("🔄 Dashboard will auto-refresh every 30 seconds")
    print("📷 Click on images to view full size")
    print("⏹️  Press Ctrl+C to stop the dashboard")
    print("="*50)
    
    # Run the Flask app
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped!")

if __name__ == '__main__':
    main()