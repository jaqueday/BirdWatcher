#!/bin/bash

# ============================================================================
# COMPLETE AI MONITORING SYSTEM SETUP for Raspberry Pi 5
# Includes all fixes, dependencies, and optimizations
# ============================================================================

echo "🚀 Starting Complete AI Monitoring System Setup..."
echo "This script will:"
echo "  - Install all required system packages"
echo "  - Fix NumPy compatibility issues"
echo "  - Install YOLO8 and dependencies"
echo "  - Configure camera permissions"
echo "  - Test the complete system"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# SYSTEM UPDATE
# ============================================================================
log_info "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# ============================================================================
# SYSTEM PACKAGES (Stable versions from Debian repos)
# ============================================================================
log_info "Installing system packages..."

# Essential development tools
sudo apt install -y python3-pip python3-dev python3-setuptools python3-wheel

# Computer vision and camera packages (system versions for stability)
sudo apt install -y python3-numpy python3-opencv python3-scipy python3-matplotlib
sudo apt install -y python3-picamera2 python3-pil

# Additional system dependencies
sudo apt install -y libatlas-base-dev libhdf5-dev libhdf5-serial-dev
sudo apt install -y build-essential cmake pkg-config
sudo apt install -y libgtk-3-dev libavcodec-dev libavformat-dev libswscale-dev

# ============================================================================
# CAMERA CONFIGURATION
# ============================================================================
log_info "Configuring camera interface..."

# Enable camera interface
sudo raspi-config nonint do_camera 0

# Set up camera permissions
sudo usermod -a -G video $USER

# Increase GPU memory split for camera operations
sudo raspi-config nonint do_memory_split 128

# ============================================================================
# FIX NUMPY COMPATIBILITY ISSUES
# ============================================================================
log_info "Fixing NumPy compatibility issues..."

# Remove any user-installed numpy/opencv that might conflict
pip3 uninstall --break-system-packages -y numpy opencv-python opencv-python-headless scipy 2>/dev/null || true

# Verify system packages are working
python3 -c "import numpy; print(f'✓ NumPy: {numpy.__version__} (system)')" || log_error "NumPy system package failed"
python3 -c "import cv2; print(f'✓ OpenCV: {cv2.__version__} (system)')" || log_error "OpenCV system package failed"

# ============================================================================
# INSTALL YOLO8 AND AI PACKAGES
# ============================================================================
log_info "Installing YOLO8 and AI packages..."

# Install ultralytics (YOLO8) with system override
pip3 install --break-system-packages ultralytics

# Install additional useful packages
pip3 install --break-system-packages imutils requests tqdm

# ============================================================================
# CREATE PROJECT STRUCTURE
# ============================================================================
log_info "Setting up project structure..."

# Create necessary directories
mkdir -p captures detections logs test_results

# Set proper permissions
chmod 755 captures detections logs test_results

# ============================================================================
# SYSTEM OPTIMIZATIONS
# ============================================================================
log_info "Applying system optimizations..."

# Increase swap for AI processing (if needed)
SWAP_SIZE=$(free -m | awk '/^Swap:/ {print $2}')
if [ "$SWAP_SIZE" -lt 2048 ]; then
    log_info "Increasing swap size for AI processing..."
    sudo dphys-swapfile swapoff
    sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
    sudo dphys-swapfile setup
    sudo dphys-swapfile swapon
fi

# Optimize for camera usage
echo 'gpu_mem=128' | sudo tee -a /boot/firmware/config.txt > /dev/null
echo 'dtoverlay=imx708' | sudo tee -a /boot/firmware/config.txt > /dev/null

# ============================================================================
# TEST INSTALLATION
# ============================================================================
log_info "Testing installation..."

echo ""
echo "Testing core components..."

# Test NumPy
if python3 -c "import numpy; print(f'✓ NumPy {numpy.__version__}')" 2>/dev/null; then
    log_success "NumPy working"
else
    log_error "NumPy failed"
fi

# Test OpenCV
if python3 -c "import cv2; print(f'✓ OpenCV {cv2.__version__}')" 2>/dev/null; then
    log_success "OpenCV working"
else
    log_error "OpenCV failed"
fi

# Test Camera
if python3 -c "from picamera2 import Picamera2; print('✓ Picamera2 working')" 2>/dev/null; then
    log_success "Camera interface working"
else
    log_warning "Camera interface may need reboot to work properly"
fi

# Test YOLO8
if python3 -c "from ultralytics import YOLO; print('✓ YOLO8 working')" 2>/dev/null; then
    log_success "YOLO8 working"
else
    log_error "YOLO8 failed"
fi

# ============================================================================
# DOWNLOAD YOLO MODEL
# ============================================================================
log_info "Pre-downloading YOLO8 model..."
python3 -c "
from ultralytics import YOLO
try:
    model = YOLO('yolov8n.pt')
    print('✓ YOLO8 model downloaded successfully')
except Exception as e:
    print(f'⚠ YOLO8 model download failed: {e}')
"

# ============================================================================
# SYSTEM SERVICE SETUP (OPTIONAL)
# ============================================================================
read -p "Do you want to set up the monitoring system as a service (auto-start on boot)? (y/n): " setup_service

if [[ $setup_service =~ ^[Yy]$ ]]; then
    log_info "Setting up systemd service..."
    
    cat > /tmp/ai-monitor.service << EOF
[Unit]
Description=AI Monitoring System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
ExecStart=/usr/bin/python3 main_monitor_with_stats.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=$PWD

[Install]
WantedBy=multi-user.target
EOF

    sudo mv /tmp/ai-monitor.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable ai-monitor.service
    
    log_success "Service installed! Control with:"
    echo "  sudo systemctl start ai-monitor    # Start"
    echo "  sudo systemctl stop ai-monitor     # Stop"
    echo "  sudo systemctl status ai-monitor   # Check status"
fi

# ============================================================================
# CLEANUP
# ============================================================================
log_info "Cleaning up..."

# Clean pip cache
pip3 cache purge 2>/dev/null || true

# Clean apt cache
sudo apt autoremove -y
sudo apt autoclean

# ============================================================================
# FINAL INSTRUCTIONS
# ============================================================================
echo ""
echo "============================================================================"
log_success "🎉 SETUP COMPLETE!"
echo "============================================================================"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1. 🔄 REBOOT YOUR RASPBERRY PI:"
echo "   sudo reboot"
echo ""
echo "2. 🧪 TEST THE SYSTEM:"
echo "   python3 main_monitor_with_stats.py"
echo ""
echo "3. 📊 VIEW STATISTICS:"
echo "   python3 view_stats.py"
echo ""
echo "4. ⚙️  CONFIGURE SETTINGS:"
echo "   nano config.json"
echo ""
echo "🎯 TESTING DETECTION:"
echo "  - Stand in front of camera (person detection)"
echo "  - Show dog/bird photos on phone screen"
echo "  - Check detections/ folder for results"
echo ""
echo "📁 KEY FILES:"
echo "  - main_monitor_with_stats.py  (main application)"
echo "  - view_stats.py               (statistics viewer)"
echo "  - config.json                 (settings)"
echo "  - monitoring.log              (system logs)"
echo ""
echo "🆘 TROUBLESHOOTING:"
echo "  - Check logs: tail -f monitoring.log"
echo "  - Test components: python3 test_system.py"
echo "  - Camera issues: check /var/log/syslog"
echo ""

# Check if reboot is needed
if [ -f /var/run/reboot-required ]; then
    log_warning "System reboot required for all changes to take effect!"
fi

log_success "Setup script completed successfully! 🚀"