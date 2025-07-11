# Pi RTK Surveyor - Testing Strategy

> **Comprehensive testing approach for development, simulation, and hardware validation**

## 🎯 Testing Philosophy

**Development → Simulation → Hardware → Field**

1. **Fast Iteration**: Local simulation for rapid development
2. **Realistic Testing**: QEMU for Pi environment validation  
3. **Hardware Validation**: Real Pi testing for GPIO/hardware interfaces
4. **Field Testing**: Actual GPS/RTK validation in field conditions

## 📋 Testing Phases

### Phase 1: Local Development Testing
**Goal**: Fast iteration and core logic validation
**Environment**: Local machine with simulation mode
**Duration**: Daily development cycles

#### Quick Development Loop
```bash
# Core application testing
python3 software/main.py --simulate --debug

# Individual component testing
python3 software/display/oled_manager.py
python3 software/monitoring/system_monitor.py
python3 software/input/button_manager.py

# Unit testing
pytest software/tests/ -v
```

#### Mock Data Setup
```bash
# Create test data directory
mkdir -p test-data/gps-samples/
mkdir -p test-data/rtk-corrections/

# Sample NMEA files for GPS testing
test-data/gps-samples/
├── stationary-fix.nmea          # Simulated base station
├── moving-rover.nmea            # Simulated rover path
├── rtk-float-to-fixed.nmea      # RTK acquisition sequence
└── poor-conditions.nmea         # Low satellite count, multipath
```

### Phase 2: QEMU Pi Environment Testing
**Goal**: Realistic Pi OS environment without hardware
**Environment**: QEMU aarch64 with Pi OS
**Duration**: Integration testing cycles

#### QEMU Setup for Pi Development
```bash
# Download Pi OS Lite image
wget https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2024-03-15/2024-03-15-raspios-lite-armhf.zip

# Extract and resize for development
unzip 2024-03-15-raspios-lite-armhf.zip
qemu-img resize 2024-03-15-raspios-lite-armhf.img 8G

# Boot Pi OS in QEMU
qemu-system-aarch64 \
  -machine raspi3b \
  -cpu cortex-a72 \
  -m 1G \
  -kernel kernel8.img \
  -dtb bcm2710-rpi-3-b.dtb \
  -sd 2024-03-15-raspios-lite-armhf.img \
  -netdev user,id=net0,hostfwd=tcp::2222-:22 \
  -device usb-net,netdev=net0 \
  -nographic
```

#### QEMU Testing Workflow
```bash
# SSH into QEMU Pi
ssh -p 2222 pi@localhost

# Install and test Pi RTK Surveyor
git clone https://github.com/hotschmoe/pi-rtk-surveyor.git
cd pi-rtk-surveyor
./install/setup.sh

# Test in QEMU environment
./test.sh
./service.sh status
```

#### QEMU Test Coverage
- ✅ **Installation Scripts** - Verify setup.sh works correctly
- ✅ **Service Management** - systemd service installation/startup
- ✅ **Python Dependencies** - Virtual environment and package installation
- ✅ **File System Operations** - Log files, configuration, data storage
- ✅ **Network Stack** - WiFi management, web interface
- ✅ **Application Logic** - Core surveying algorithms
- ❌ **Hardware Interfaces** - GPIO, SPI, I2C (requires mocking)

### Phase 3: Hardware Validation Testing
**Goal**: Validate hardware interfaces and GPIO functionality
**Environment**: Actual Raspberry Pi with attached HATs
**Duration**: Hardware integration cycles

#### Hardware Test Sequence
```bash
# 1. Basic Pi functionality
./test.sh                           # Basic simulation test
./service.sh status                 # Service management

# 2. Hardware interface validation
sudo i2cdetect -y 1                 # Verify I2C devices
ls -la /dev/spi*                    # Verify SPI devices
gpio readall                        # Check GPIO status

# 3. OLED display testing
python3 software/display/oled_manager.py  # Direct OLED test
python3 software/main.py --debug          # Full app with hardware

# 4. Button interface testing
python3 software/input/button_manager.py  # Button event testing

# 5. GPS module testing
python3 software/gnss/lc29h_controller.py # GPS communication
cat /dev/ttyAMA0                           # Raw serial data
```

#### Hardware Validation Checklist
- [ ] **Power Management** - Battery monitoring, power consumption
- [ ] **OLED Display** - All screen modes, brightness control
- [ ] **Button Interface** - All 3 keys + joystick directions
- [ ] **GPS Module** - NMEA parsing, position acquisition
- [ ] **WiFi Communication** - Hotspot creation, client connection
- [ ] **File System** - Data logging, configuration persistence
- [ ] **System Services** - Auto-start, clean shutdown

### Phase 4: Field Testing
**Goal**: Real-world GPS and RTK validation
**Environment**: Outdoor location with clear sky view
**Duration**: Field validation cycles

#### Field Test Scenarios
```bash
# Indoor GPS acquisition test
python3 software/main.py --debug
# Verify: GPS status, satellite count, position accuracy

# Outdoor RTK base station test
python3 software/main.py --mode=base --debug
# Verify: GPS fix, RTK corrections, WiFi broadcast

# Outdoor RTK rover test  
python3 software/main.py --mode=rover --debug
# Verify: RTK corrections received, cm-level accuracy

# Survey point logging test
# Verify: Point capture, CSV logging, accuracy reporting
```

## 🔧 Development Testing Tools

### Mock GPS Data Generator
```python
# software/tests/mock_gps.py
class MockGPSController:
    def __init__(self, scenario="stationary"):
        self.scenarios = {
            "stationary": self.generate_stationary_fix(),
            "moving": self.generate_moving_path(),
            "rtk_acquisition": self.generate_rtk_sequence()
        }
        
    def generate_stationary_fix(self):
        # Generate realistic NMEA sentences for base station
        return [
            "$GNGGA,123456.00,4012.34567,N,07401.23456,W,4,12,0.8,45.2,M,-33.2,M,1.2,0000*5A",
            "$GNRMC,123456.00,A,4012.34567,N,07401.23456,W,0.0,0.0,150324,,,A*73"
        ]
```

### Button Simulation Interface
```python
# software/tests/mock_buttons.py
class MockButtonManager:
    def __init__(self):
        self.key_mappings = {
            'k': 'KEY1',    # Mode selection
            'j': 'KEY2',    # Settings
            'l': 'KEY3',    # Action/logging
            'w': 'JOY_UP',
            's': 'JOY_DOWN',
            'a': 'JOY_LEFT',
            'd': 'JOY_RIGHT',
            ' ': 'JOY_PRESS'
        }
        
    def simulate_keyboard_input(self):
        # Convert keyboard input to button events
        pass
```

### Web-Based Test Interface
```python
# software/tests/web_test_interface.py
from flask import Flask, render_template, jsonify

app = Flask(__name__)

@app.route('/test-display/<mode>')
def test_display_mode(mode):
    # Trigger different display modes
    oled_manager.show_screen(mode)
    return jsonify({"status": "ok", "mode": mode})

@app.route('/simulate-button/<button>')
def simulate_button_press(button):
    # Simulate button press for testing
    button_manager.simulate_press(button)
    return jsonify({"status": "pressed", "button": button})
```

## 🎯 Test Data Management

### Directory Structure
```
test-data/
├── gps-samples/
│   ├── indoor-no-fix.nmea
│   ├── outdoor-2d-fix.nmea
│   ├── outdoor-3d-fix.nmea
│   ├── rtk-float.nmea
│   └── rtk-fixed.nmea
├── rtk-corrections/
│   ├── base-station-rtcm3.bin
│   └── simulated-corrections.rtcm
├── survey-data/
│   ├── sample-property-points.csv
│   └── validation-coordinates.csv
└── config/
    ├── base-station-config.json
    └── rover-config.json
```

### Test Configuration Files
```json
// test-data/config/test-base-config.json
{
    "device_id": "TEST-BASE-001",
    "mode": "base_station",
    "gps": {
        "mock_data_file": "test-data/gps-samples/rtk-fixed.nmea",
        "update_rate": 1.0
    },
    "wifi": {
        "ssid": "TEST-RTK-BASE",
        "password": "test12345"
    },
    "logging": {
        "level": "DEBUG",
        "log_gps_raw": true
    }
}
```

## 🚀 Testing Automation

### Continuous Integration Tests
```bash
# .github/workflows/test.yml
name: Pi RTK Surveyor Tests

on: [push, pull_request]

jobs:
  simulation-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install -r install/requirements.txt
    - name: Run simulation tests
      run: |
        python3 software/main.py --simulate --test-mode
        pytest software/tests/ -v
```

### Hardware Test Scripts
```bash
# scripts/hardware-test.sh
#!/bin/bash
echo "Pi RTK Surveyor Hardware Validation"
echo "===================================="

# Test 1: Service status
echo "1. Testing service status..."
./service.sh status

# Test 2: Hardware interfaces
echo "2. Testing hardware interfaces..."
sudo i2cdetect -y 1
ls -la /dev/spi*

# Test 3: OLED display
echo "3. Testing OLED display..."
timeout 10s python3 software/display/oled_manager.py

# Test 4: Button interface
echo "4. Testing button interface..."
echo "Press KEY1, KEY2, KEY3 within 10 seconds..."
timeout 10s python3 software/input/button_manager.py

# Test 5: GPS module
echo "5. Testing GPS module..."
timeout 30s python3 software/gnss/lc29h_controller.py

echo "Hardware validation complete!"
```

## 📊 Test Coverage Goals

### Unit Tests
- [ ] **Display Manager** - All screen modes, brightness control
- [ ] **Button Manager** - Event handling, debouncing
- [ ] **GPS Controller** - NMEA parsing, coordinate conversion
- [ ] **System Monitor** - Resource monitoring, battery level
- [ ] **Configuration** - Settings load/save, validation
- [ ] **Data Logging** - CSV export, file management

### Integration Tests
- [ ] **OLED + System Monitor** - Real-time display updates
- [ ] **Button + Display** - Menu navigation, mode switching
- [ ] **GPS + Display** - Position display, accuracy indicators
- [ ] **RTK Base + Rover** - Correction transmission/reception
- [ ] **Web Interface** - Data download, configuration

### End-to-End Tests
- [ ] **Complete Survey Workflow** - Base setup → rover operation → data export
- [ ] **Field Operation** - Battery life, GPS accuracy, data integrity
- [ ] **Error Handling** - Hardware failures, poor GPS conditions
- [ ] **Performance** - Memory usage, CPU load, response times

## 🔍 Hardware Validation Checklist

### Pre-Installation Validation
- [ ] **Physical Assembly** - HAT stacking, GPIO connections
- [ ] **Power Supply** - Voltage levels, current consumption
- [ ] **Hardware Interfaces** - SPI/I2C device detection
- [ ] **Display Functionality** - OLED initialization, pixel test
- [ ] **Button Response** - All keys and joystick directions

### Post-Installation Validation
- [ ] **Service Management** - Auto-start, clean shutdown
- [ ] **Network Configuration** - WiFi hotspot, client connection
- [ ] **GPS Acquisition** - Time to first fix, accuracy
- [ ] **RTK Performance** - Correction latency, fix quality
- [ ] **Data Integrity** - Survey point logging, file persistence
- [ ] **Battery Management** - Level monitoring, low power warnings

### Field Validation
- [ ] **GPS Performance** - Outdoor fix time, accuracy
- [ ] **RTK Range** - Base-rover communication distance
- [ ] **Survey Accuracy** - Known point validation
- [ ] **Environmental** - Temperature, humidity, vibration
- [ ] **Operational** - Battery life, user interface

## 🎯 Testing Schedule

### Development Phase (Week 1-2)
- **Day 1-3**: Local simulation testing, core modules
- **Day 4-5**: QEMU integration testing, service management
- **Day 6-7**: Hardware validation, OLED/button interfaces

### Integration Phase (Week 3)
- **Day 1-2**: GPS module integration, NMEA parsing
- **Day 3-4**: RTK communication, base-rover functionality
- **Day 5-7**: Field testing, accuracy validation

### Deployment Phase (Week 4)
- **Day 1-2**: Final integration testing, bug fixes
- **Day 3-4**: Field deployment, operational testing
- **Day 5-7**: Documentation, performance optimization

---

**Ready for development testing?** Run `./test.sh` to begin simulation validation.  
**Hardware ready?** Execute `scripts/hardware-test.sh` for full validation.  
**Field testing?** Follow the field validation checklist above.
