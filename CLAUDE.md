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

### GPIO Pin Allocations
- SPI for OLED display (pins 19, 23, 24 + GPIO 24, 25)
- I2C for additional sensors
- GPIO pins 21, 20, 16 for buttons (KEY1, KEY2, KEY3)
- Joystick on GPIO pins 6, 19, 5, 26, 13

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

## Important Notes

- Never run setup.sh as root - it handles sudo internally where needed
- Hardware interfaces (SPI/I2C) must be enabled via raspi-config before first use
- The system uses systemd for service management with security restrictions
- All hardware operations require actual GPIO pins - this is not a simulation-friendly codebase
- **Simplified Architecture**: All functionality is integrated into main.py - no separate modules to import
- Mode selection (BASE/ROVER) switches operational states within the same running application
- Button events are processed through a centralized ButtonAPI system with mode-specific handlers
- Display updates use the luma.oled library with custom screen implementations