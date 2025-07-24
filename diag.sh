#!/bin/bash

# NumPy Compatibility Fix Script
# Fixes the "numpy.dtype size changed" error with simplejpeg

echo "🔧 FIXING NUMPY COMPATIBILITY ISSUE"
echo "====================================="
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

# Check current NumPy version
log_info "Checking current NumPy version..."
NUMPY_VERSION=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "Not found")
echo "Current NumPy version: $NUMPY_VERSION"

# Show the error details
log_info "The error indicates simplejpeg was compiled against a different NumPy version"
echo "This happens when mixing system packages (apt) with pip packages"

# Method 1: Try reinstalling simplejpeg with pip (force rebuild)
log_info "Method 1: Reinstalling simplejpeg to rebuild against current NumPy..."

# First, try to reinstall simplejpeg
pip3 install --break-system-packages --force-reinstall --no-cache-dir simplejpeg

if [ $? -eq 0 ]; then
    log_success "Simplejpeg reinstalled successfully"
    
    # Test if the issue is fixed
    log_info "Testing if the issue is fixed..."
    python3 -c "
try:
    from picamera2 import Picamera2
    print('✅ Picamera2 import successful!')
except Exception as e:
    print(f'❌ Still failing: {e}')
    exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "🎉 ISSUE FIXED! Picamera2 is working now"
        exit 0
    fi
fi

log_warning "Method 1 didn't work, trying Method 2..."

# Method 2: Use system package for simplejpeg
log_info "Method 2: Installing system simplejpeg package..."

# Remove pip version and install system version
pip3 uninstall --break-system-packages -y simplejpeg 2>/dev/null
sudo apt update
sudo apt install -y python3-simplejpeg

# Test again
log_info "Testing with system simplejpeg package..."
python3 -c "
try:
    from picamera2 import Picamera2
    print('✅ Picamera2 import successful!')
except Exception as e:
    print(f'❌ Still failing: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    log_success "🎉 ISSUE FIXED! Using system simplejpeg package"
    exit 0
fi

log_warning "Method 2 didn't work, trying Method 3..."

# Method 3: Downgrade/upgrade NumPy to match compiled version
log_info "Method 3: Trying to fix NumPy version compatibility..."

# Try installing a specific NumPy version that's more compatible
pip3 install --break-system-packages --force-reinstall "numpy>=1.21.0,<1.25.0"

# Reinstall simplejpeg after NumPy change
pip3 install --break-system-packages --force-reinstall --no-cache-dir simplejpeg

# Test again
log_info "Testing with adjusted NumPy version..."
python3 -c "
try:
    from picamera2 import Picamera2
    print('✅ Picamera2 import successful!')
    import numpy
    print(f'NumPy version: {numpy.__version__}')
except Exception as e:
    print(f'❌ Still failing: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    log_success "🎉 ISSUE FIXED! NumPy version adjusted"
    exit 0
fi

log_warning "Method 3 didn't work, trying Method 4..."

# Method 4: Complete package reset
log_info "Method 4: Complete package reset (last resort)..."

log_warning "This will remove and reinstall camera packages. Continue? (y/n)"
read -r continue_reset

if [ "$continue_reset" = "y" ]; then
    # Remove all related packages
    pip3 uninstall --break-system-packages -y simplejpeg picamera2 2>/dev/null
    sudo apt remove -y python3-picamera2 python3-simplejpeg 2>/dev/null
    
    # Reinstall from system packages
    sudo apt update
    sudo apt install -y python3-picamera2 python3-simplejpeg python3-numpy python3-opencv
    
    # Test final result
    log_info "Testing after complete reset..."
    python3 -c "
try:
    from picamera2 import Picamera2
    print('✅ Picamera2 import successful!')
    import numpy
    print(f'NumPy version: {numpy.__version__}')
except Exception as e:
    print(f'❌ Still failing: {e}')
    exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "🎉 ISSUE FIXED! Complete reset successful"
    else
        log_error "All methods failed. This may require a system update or reboot."
        echo ""
        echo "🆘 MANUAL FIXES TO TRY:"
        echo "1. Reboot the system: sudo reboot"
        echo "2. Update all packages: sudo apt update && sudo apt upgrade"
        echo "3. Check system logs: dmesg | grep -i error"
        echo "4. Try a fresh virtual environment"
    fi
else
    log_info "Skipping complete reset"
fi

echo ""
echo "====================================="
log_info "Fix attempt completed"
echo "====================================="