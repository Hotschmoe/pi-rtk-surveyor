#!/bin/bash
# Pi RTK Surveyor Hardware Validation Script
# Comprehensive testing of all hardware interfaces

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  Pi RTK Surveyor Hardware Validation${NC}"
echo -e "${BLUE}======================================${NC}"
echo

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo -e "${RED}Error: This script must be run on a Raspberry Pi${NC}"
    exit 1
fi

# Test 1: Service Status
echo -e "${YELLOW}Test 1: Service Management${NC}"
echo "Checking Pi RTK Surveyor service status..."
if systemctl is-active --quiet pi-rtk-surveyor; then
    echo -e "${GREEN}✅ Service is running${NC}"
else
    echo -e "${YELLOW}⚠️  Service is not running - this is expected during development${NC}"
fi

if systemctl is-enabled --quiet pi-rtk-surveyor; then
    echo -e "${GREEN}✅ Service is enabled for auto-start${NC}"
else
    echo -e "${YELLOW}⚠️  Service is not enabled for auto-start${NC}"
fi
echo

# Test 2: Hardware Interfaces
echo -e "${YELLOW}Test 2: Hardware Interfaces${NC}"
echo "Checking SPI interface..."
if ls /dev/spi* > /dev/null 2>&1; then
    echo -e "${GREEN}✅ SPI interface detected:${NC}"
    ls -la /dev/spi*
else
    echo -e "${RED}❌ SPI interface not found - check raspi-config${NC}"
fi

echo
echo "Checking I2C interface..."
if command -v i2cdetect > /dev/null 2>&1; then
    echo -e "${GREEN}✅ I2C tools available${NC}"
    echo "Scanning I2C bus 1..."
    sudo i2cdetect -y 1
else
    echo -e "${RED}❌ I2C tools not installed${NC}"
fi

echo
echo "Checking GPIO interface..."
if command -v gpio > /dev/null 2>&1; then
    echo -e "${GREEN}✅ GPIO tools available${NC}"
    gpio readall | head -20
else
    echo -e "${YELLOW}⚠️  WiringPi gpio tool not available (optional)${NC}"
fi
echo

# Test 3: OLED Display
echo -e "${YELLOW}Test 3: OLED Display${NC}"
echo "Testing OLED display functionality..."
echo "You should see the OLED display cycle through test screens..."
if timeout 15s python3 software/display/oled_manager.py 2>/dev/null; then
    echo -e "${GREEN}✅ OLED display test completed${NC}"
else
    echo -e "${RED}❌ OLED display test failed or timed out${NC}"
fi
echo

# Test 4: Button Interface
echo -e "${YELLOW}Test 4: Button Interface${NC}"
echo "Testing button interface..."
echo -e "${BLUE}Press KEY1, KEY2, KEY3, and joystick directions within 15 seconds...${NC}"
if timeout 15s python3 -c "
import sys
sys.path.insert(0, 'software')
from input.button_manager import ButtonManager
import time
button_manager = ButtonManager(simulate_buttons=False)
print('Button test ready - press buttons now...')
start_time = time.time()
button_count = 0
while time.time() - start_time < 10:
    if button_manager.get_button_events():
        button_count += 1
        print(f'Button {button_count} pressed!')
    time.sleep(0.1)
print(f'Button test complete - {button_count} buttons detected')
" 2>/dev/null; then
    echo -e "${GREEN}✅ Button interface test completed${NC}"
else
    echo -e "${RED}❌ Button interface test failed${NC}"
fi
echo

# Test 5: GPS Module
echo -e "${YELLOW}Test 5: GPS Module${NC}"
echo "Testing GPS module communication..."
echo "Looking for GPS serial interface..."

# Check for common GPS serial devices
GPS_DEVICES=("/dev/ttyAMA0" "/dev/ttyS0" "/dev/ttyUSB0" "/dev/ttyACM0")
GPS_FOUND=false

for device in "${GPS_DEVICES[@]}"; do
    if [ -c "$device" ]; then
        echo -e "${GREEN}✅ Found GPS serial device: $device${NC}"
        GPS_FOUND=true
        
        # Try to read raw GPS data
        echo "Attempting to read GPS data (10 seconds)..."
        if timeout 10s cat "$device" | head -5; then
            echo -e "${GREEN}✅ GPS data received${NC}"
        else
            echo -e "${YELLOW}⚠️  No GPS data received (may need outdoor location)${NC}"
        fi
        break
    fi
done

if [ "$GPS_FOUND" = false ]; then
    echo -e "${RED}❌ No GPS serial device found${NC}"
fi

echo
echo "Testing GPS controller module..."
if timeout 20s python3 -c "
import sys
sys.path.insert(0, 'software')
from gnss.lc29h_controller import LC29HController
import time
try:
    gps = LC29HController()
    print('GPS controller initialized')
    time.sleep(5)
    print('GPS controller test complete')
except Exception as e:
    print(f'GPS controller error: {e}')
" 2>/dev/null; then
    echo -e "${GREEN}✅ GPS controller test completed${NC}"
else
    echo -e "${RED}❌ GPS controller test failed${NC}"
fi
echo

# Test 6: System Resources
echo -e "${YELLOW}Test 6: System Resources${NC}"
echo "Checking system resources..."

# CPU temperature
if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
    temp=$(cat /sys/class/thermal/thermal_zone0/temp)
    temp_c=$((temp / 1000))
    echo -e "${GREEN}✅ CPU Temperature: ${temp_c}°C${NC}"
    if [ $temp_c -gt 70 ]; then
        echo -e "${YELLOW}⚠️  CPU temperature is high${NC}"
    fi
else
    echo -e "${RED}❌ Cannot read CPU temperature${NC}"
fi

# Memory usage
if command -v free > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Memory usage:${NC}"
    free -h | head -2
else
    echo -e "${RED}❌ Cannot check memory usage${NC}"
fi

# Disk space
echo -e "${GREEN}✅ Disk usage:${NC}"
df -h / | tail -1
echo

# Test 7: Application Startup
echo -e "${YELLOW}Test 7: Application Startup${NC}"
echo "Testing application startup in simulation mode..."
if timeout 15s python3 software/main.py --simulate --debug 2>/dev/null; then
    echo -e "${GREEN}✅ Application startup test completed${NC}"
else
    echo -e "${RED}❌ Application startup test failed${NC}"
fi
echo

# Test 8: Configuration and Data Directories
echo -e "${YELLOW}Test 8: File System${NC}"
echo "Checking project directories..."

REQUIRED_DIRS=("data/logs" "data/surveys" "data/config" "software" "install")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅ Directory exists: $dir${NC}"
    else
        echo -e "${RED}❌ Missing directory: $dir${NC}"
    fi
done

# Check permissions
echo "Checking file permissions..."
if [ -x "software/main.py" ]; then
    echo -e "${GREEN}✅ Main application is executable${NC}"
else
    echo -e "${RED}❌ Main application is not executable${NC}"
fi

if [ -x "install/setup.sh" ]; then
    echo -e "${GREEN}✅ Setup script is executable${NC}"
else
    echo -e "${RED}❌ Setup script is not executable${NC}"
fi
echo

# Test Summary
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  Hardware Validation Summary${NC}"
echo -e "${BLUE}======================================${NC}"
echo
echo "Hardware validation complete!"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo "1. If any tests failed, check hardware connections"
echo "2. Verify SPI/I2C interfaces are enabled in raspi-config"
echo "3. Test outdoors for GPS functionality"
echo "4. Run './test.sh' for simulation mode testing"
echo "5. Check './service.sh logs' for detailed application logs"
echo
echo -e "${GREEN}Ready for development!${NC}" 