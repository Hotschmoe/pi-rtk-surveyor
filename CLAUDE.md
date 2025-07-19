# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Pi RTK Surveyor project that creates a professional-grade RTK surveying station using a Raspberry Pi. The system provides centimeter-level GPS accuracy for property mapping and topographical surveying at a fraction of the cost of commercial solutions.

## Architecture

The codebase uses a simplified, integrated architecture:

### Core Components
- **main.py**: Integrated application containing bootloader, base station, and rover functionality
- **hardware/**: Hardware abstraction layer for GPIO, OLED display, buttons, and system monitoring
- **common/**: Shared utilities including GPS controller, NMEA parsing, data logging, and communication protocols
- **web/**: Web interface for base station remote monitoring

### Key Architecture Patterns
- All functionality is contained in a single PiRTKSurveyor class in main.py
- Hardware components are initialized once and shared across all modes
- Mode selection switches between different operational states within the same application
- GPIO management is centralized through gpio_manager.py
- Display management uses luma.oled with custom screens and UI elements
- System runs as a systemd service with proper resource limits and security settings

## Development Commands

### Installation and Setup
```bash
# Initial setup (run as regular user, not root)
./setup.sh

# Enable SPI/I2C interfaces after setup
sudo raspi-config
# Interface Options > SPI > Enable
# Interface Options > I2C > Enable

# CRITICAL: Disable Bluetooth to free UART for GPS
sudo bash -c 'echo "dtoverlay=disable-bt" >> /boot/firmware/config.txt'
sudo systemctl disable hciuart.service
sudo systemctl disable bluetooth.service

# Reboot to apply all changes
sudo reboot
```

### Running the Application
```bash
# Start manually
./start.sh

# Service management
./service.sh start|stop|restart|status|logs|enable|disable

# Run with specific log level
python3 src/main.py --log-level DEBUG
```

### Python Environment
- Uses virtual environment at `./venv/`
- Dependencies managed via `requirements.txt`
- All Python commands should use `./venv/bin/python`

### Testing and Development
```bash
# View live logs
./service.sh logs

# Check system status
./service.sh status

# Manual testing (stop service first)
./service.sh stop
python3 src/main.py --log-level DEBUG
```

## Hardware Dependencies

This project is designed for real hardware testing only - no simulation modes:
- Raspberry Pi Zero W 2 (or any Pi with GPIO)
- LC29H GNSS RTK HAT for GPS functionality
- Waveshare 1.3" OLED HAT for display and button controls
- Requires SPI and I2C interfaces enabled
- **CRITICAL**: Bluetooth must be disabled to free UART for GPS communication

### GPIO Pin Allocations
- **UART** for LC29H GPS (pins 8/10 - TXD/RXD)
- SPI for OLED display (pins 19, 23, 24 + GPIO 24, 25)
- I2C for additional sensors
- GPIO pins 21, 20, 16 for buttons (KEY1, KEY2, KEY3)
- Joystick on GPIO pins 6, 19, 5, 26, 13

### UART Configuration Requirements
The LC29H GPS module requires exclusive access to the Pi's main UART (/dev/ttyAMA0). By default, Raspberry Pi OS assigns this UART to Bluetooth, which prevents GPS communication. The system automatically disables Bluetooth during setup to ensure GPS functionality.

## Key Files to Understand

- `src/main.py`: Complete application with bootloader, base station, and rover functionality
  - `PiRTKSurveyor.run()`: Main application loop
  - `_start_base_station()`: Base station mode initialization and operation
  - `_start_rover()`: Rover mode initialization and operation
- `src/hardware/gpio_manager.py`: Centralized GPIO pin management
- `src/hardware/oled_manager.py`: Display management using luma.oled
- `src/hardware/button_api.py`: Button event handling system
- `src/common/lc29h_controller.py`: GPS module interface
- `src/common/config/settings.py`: Configuration management

## Data Storage

- Logs: `data/logs/`
- Survey data: `data/surveys/`
- Configuration: `src/common/config/device_config.json`
- System logs: `journalctl -u pi-rtk-surveyor`

## Implementation Status

### ✅ Completed Components
- **LC29H GPS Controller**: Full NMEA parsing, RTK detection, position callbacks (`src/common/lc29h_controller.py`)
- **Web Dashboard**: Flask + SocketIO server with real-time monitoring (`src/web/web_server.py`)
- **Hardware Abstraction**: GPIO, OLED display, button management (`src/hardware/`)
- **Main Application**: Integrated bootloader with base/rover mode switching (`src/main.py`)
- **Dependencies**: All required packages defined in `requirements.txt`

### 🚧 In Progress / Needs Implementation
- **GNSS Hardware Integration**: GPS controller exists but needs proper initialization in main.py
- **Point Logging System**: Basic structure exists but needs full implementation
- **Data Logging**: Files exist but are mostly placeholder implementations
- **WiFi Hotspot Management**: Placeholder implementation (to be developed but not enabled)
- **Multi-Sector Survey Support**: Not yet implemented

### 📋 Implementation Roadmap

#### Phase 1: Core GNSS Functionality (Priority: HIGH)
1. **GNSS Hardware Initialization**
   - Integrate LC29H controller properly in main.py
   - Add hardware initialization sequence for real GPS module
   - Test RTK functionality with actual hardware

2. **Point Logging System**
   - Implement robust point logging in `src/common/data_logging/data_logger.py`
   - Add CSV export functionality
   - Create point validation and accuracy checking

#### Phase 2: Base Station Operations (Priority: HIGH)  
3. **WiFi Hotspot Preparation**
   - Develop WiFi hotspot management in `src/common/communication/wifi_manager.py`
   - Create configuration but keep disabled for development
   - Add hotspot status monitoring

4. **Web Dashboard Simplification**
   - Remove config settings pages (keep only dashboard)
   - Focus on real-time monitoring interface
   - Optimize for mobile/tablet viewing

#### Phase 3: Multi-Sector Surveys (Priority: MEDIUM)
5. **Multi-Sector Survey System**
   - Design sector-based data organization
   - Implement base station repositioning workflow
   - Add sector merging/export for CAD integration
   - Support for 10+ acre surveys with multiple base positions

6. **Data Management**
   - Sector-based file organization
   - GPS coordinate transformation between sectors
   - Export formats for CAD software integration

### 🎯 Detailed Implementation Plan

#### Task 1: GNSS Hardware Integration (IMMEDIATE)
**File**: `src/main.py` (lines 92-94, 122-124)
**Goal**: Replace GPS simulation with real hardware initialization

**Current Issue**: GPS controller is initialized but runs in simulation mode
```python
# Current (line 93): 
self.gps_controller = LC29HController()
# Needs to become:
self.gps_controller = LC29HController(port='/dev/ttyAMA0', baudrate=38400, simulate=False)
```

**Implementation Steps**:
1. Add GPS hardware detection in `initialize_hardware()` method
2. Implement fallback to simulation if hardware not detected
3. Add proper error handling for GPS connection failures
4. Update `_update_monitoring_data()` to use real GPS data instead of placeholders
5. Test with actual LC29H RTK HAT hardware

#### Task 2: Point Logging System (HIGH PRIORITY)
**Files**: `src/common/data_logging/data_logger.py`, `src/main.py`
**Goal**: Implement robust survey point logging with CSV export

**Required Features**:
- Point validation (RTK fixed/float required)
- CSV file format with timestamps, coordinates, accuracy
- Point numbering and naming system
- Data persistence and recovery
- Real-time logging feedback on OLED display

**Implementation Steps**:
1. Complete `DataLogger` class in `data_logger.py`
2. Add CSV export functionality 
3. Integrate logging in `_log_survey_point()` method (main.py:562)
4. Add visual feedback for successful point logging
5. Implement point history and management

#### Task 3: WiFi Hotspot Management (MEDIUM PRIORITY - DEVELOP BUT KEEP DISABLED)
**File**: `src/common/communication/wifi_manager.py`
**Goal**: Create WiFi hotspot capability for base station (keep disabled during development)

**Required Features**:
- Hotspot creation and management
- DHCP server configuration
- Network isolation for rover connections
- Hotspot status monitoring
- Configuration persistence

**Implementation Steps**:
1. Implement `WiFiManager` class with hotspot methods
2. Add hostapd configuration management
3. Create DHCP server configuration
4. Add status monitoring and error handling
5. Keep hotspot disabled by default in configuration

#### Task 4: Multi-Sector Survey System (FUTURE)
**Files**: New files in `src/common/survey/`, updates to `data_logger.py`
**Goal**: Support large surveys requiring multiple base station positions

**Required Features**:
- Sector-based data organization (Survey → Sectors → Points)
- Base station repositioning workflow
- Coordinate system transformation between sectors
- Data merging and export for CAD software
- Sector boundary management

**Implementation Steps**:
1. Design survey/sector data structure
2. Create sector management classes
3. Implement coordinate transformation algorithms
4. Add sector-aware point logging
5. Create CAD export formats (DXF, CSV with proper coordinate systems)

#### Task 5: Web Dashboard Simplification (LOW PRIORITY)
**Files**: `src/web/templates/`, `src/web/web_server.py`
**Goal**: Simplify web interface to focus only on monitoring (remove config pages)

**Changes Needed**:
1. Remove config.html template and routes
2. Focus dashboard.html on real-time monitoring only
3. Optimize for mobile/tablet viewing
4. Remove configuration API endpoints that change hardware settings

### 🔧 Development Commands for Implementation

```bash
# Test GPS hardware integration
./service.sh stop
python3 src/main.py --log-level DEBUG

# Test point logging
# [After implementation] Use KEY3 button in rover mode to log points

# Test web dashboard
# [After web server starts] Visit http://pi-ip:5000 for dashboard

# Check data files
ls -la data/surveys/
cat data/surveys/latest_survey.csv

# Troubleshooting GPS connection
# Check if UART devices exist
ls -la /dev/tty* | grep -E "(AMA|serial)"

# Check if Bluetooth is disabled
dmesg | grep -i uart
# Should NOT show "hci_uart_bcm" if Bluetooth is properly disabled

# Test UART directly
sudo cat /dev/ttyAMA0
# Should show NMEA sentences starting with $ if GPS is working
```

## Testing Philosophy

**We will not test with simulated data. We will develop for production, and a developer will test on real hardware for validation.**

This project is designed from the ground up for real hardware operation. All development assumes:
- Actual LC29H GNSS RTK HAT hardware
- Real GPIO pins and hardware interfaces
- Production-grade error handling and recovery
- True RTK performance validation

Simulation modes are provided only as fallbacks when hardware is not detected, not for primary development or testing. All features must be validated on actual Raspberry Pi hardware with the LC29H RTK HAT before being considered complete.

## Important Notes

- Never run setup.sh as root - it handles sudo internally where needed
- Hardware interfaces (SPI/I2C) must be enabled via raspi-config before first use
- The system uses systemd for service management with security restrictions
- All hardware operations require actual GPIO pins - this is not a simulation-friendly codebase
- **Simplified Architecture**: All functionality is integrated into main.py - no separate modules to import
- Mode selection (BASE/ROVER) switches operational states within the same running application
- Button events are processed through a centralized ButtonAPI system with mode-specific handlers
- Display updates use the luma.oled library with custom screen implementations
- **Development Strategy**: Keep WiFi hotspot disabled during development to maintain Pi connectivity
- **Testing Requirements**: All features must be validated on real hardware before release