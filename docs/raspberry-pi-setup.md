# Raspberry Pi Setup Guide

Complete setup instructions for installing Pi RTK Surveyor on a Raspberry Pi Zero W 2.

## Prerequisites

### Hardware Required
- Raspberry Pi Zero W 2 (or any Pi with GPIO)
- LC29H GNSS RTK HAT
- Waveshare 1.3" OLED HAT  
- MicroSD card (32GB+ recommended)
- Power supply or battery pack

### Software Prerequisites
- Fresh Raspberry Pi OS Lite installation
- SSH enabled (for headless setup)
- Internet connection

## Quick Start Installation

### 1. Clone Repository
```bash
# SSH into your Raspberry Pi
ssh pi@raspberrypi.local

# Clone the project
git clone https://github.com/hotschmoe/pi-rtk-surveyor.git
cd pi-rtk-surveyor
```

### 2. Run Installation Script
```bash
# Make setup script executable
chmod +x setup.sh

# Run installation (do NOT use sudo)
./setup.sh
```

### 3. Reboot and Test
```bash
# Reboot to enable SPI/I2C
sudo reboot
```

## Detailed Installation Steps

### Step 1: System Preparation

Update your Raspberry Pi:
```bash
sudo apt update && sudo apt upgrade -y
```

Enable required interfaces:
```bash
sudo raspi-config
# Navigate to: Interface Options > SPI > Enable
# Navigate to: Interface Options > I2C > Enable
# Navigate to: Interface Options > SSH > Enable (if not already)
```

### Step 2: Hardware Interfaces

The installation script automatically enables SPI and I2C, but you can verify:

```bash
# Check if SPI and I2C are enabled
lsmod | grep spi
lsmod | grep i2c

# List I2C devices (should show OLED if connected)
sudo i2cdetect -y 1

# Check SPI devices
ls -la /dev/spi*
```

### Step 2b: CRITICAL - Disable Bluetooth for GPS

**The LC29H GPS module requires exclusive access to the Pi's UART.** By default, Raspberry Pi OS assigns the main UART to Bluetooth, which prevents GPS communication.

```bash
# Disable Bluetooth to free UART for GPS
sudo bash -c 'echo "dtoverlay=disable-bt" >> /boot/firmware/config.txt'
sudo systemctl disable hciuart.service
sudo systemctl disable bluetooth.service

# Verify UART is available after reboot
ls -la /dev/tty* | grep -E "(AMA|serial)"
# Should show /dev/ttyAMA0 after reboot
```

**Why this is necessary:**
- LC29H GPS HAT communicates via UART (pins 8/10)
- Pi OS uses this UART for Bluetooth by default  
- GPS cannot function while Bluetooth claims the UART
- Disabling Bluetooth frees the UART for GPS exclusive use

### Step 3: Service Management

After installation, the Pi RTK Surveyor runs as a systemd service:

#### Check Service Status
```bash
# View current status
sudo systemctl status pi-rtk-surveyor

# Or use the helper script
./service.sh status
```

#### Control Service
```bash
# Start service
./service.sh start

# Stop service  
./service.sh stop

# Restart service
./service.sh restart

# View live logs
./service.sh logs

# Disable auto-start
./service.sh disable

# Enable auto-start
./service.sh enable
```

#### View Logs
```bash
# System logs
sudo journalctl -u pi-rtk-surveyor -f

# Application logs
tail -f data/logs/rtk_surveyor.log

# Or use helper script
./service.sh logs
```

#### Manual Start (for debugging)
```bash
# Stop the service first
./service.sh stop

# Run manually
./start.sh

# Or with debug output:
python3 src/main.py --log-level DEBUG
```

## Hardware Configuration

### Pin Connections TODO: VERIFY THIS

The Waveshare 1.3" OLED HAT uses these pins:
```
VCC   → 3.3V (Pin 1)
GND   → Ground (Pin 6) 
DIN   → SPI MOSI (Pin 19, GPIO 10)
CLK   → SPI SCLK (Pin 23, GPIO 11)
CS    → SPI CE0 (Pin 24, GPIO 8)
DC    → GPIO 24 (Pin 18)
RST   → GPIO 25 (Pin 22)
```

Buttons:
```
KEY1  → GPIO 21 (Pin 40)
KEY2  → GPIO 20 (Pin 38)  
KEY3  → GPIO 16 (Pin 36)
Joystick Up    → GPIO 6 (Pin 31)
Joystick Down  → GPIO 19 (Pin 35)
Joystick Left  → GPIO 5 (Pin 29)
Joystick Right → GPIO 26 (Pin 37)
Joystick Press → GPIO 13 (Pin 33)
```

### Hardware Stack Order
```
Bottom → Top:
1. Raspberry Pi Zero W 2
2. LC29H GNSS HAT (with GPIO extender pins)
3. Waveshare 1.3" OLED HAT
```

## Configuration Files

### Service Configuration
Location: `/etc/systemd/system/pi-rtk-surveyor.service`

To modify service settings:
```bash
sudo systemctl edit pi-rtk-surveyor
```

### Application Configuration TODO: UPDATE SINCE REFACTOR
Location: `software/config/device_config.json`

Example configuration:
```json
{
    "device_id": "RTK-001",
    "display": {
        "brightness": 255,
        "contrast": 128,
        "timeout": 300
    },
    "logging": {
        "level": "INFO",
        "max_files": 10
    }
}
```

## Troubleshooting

### Common Issues

#### 1. GPS Module Not Detected
```bash
# Check if UART devices exist
ls -la /dev/tty* | grep -E "(AMA|serial)"
# Should show /dev/ttyAMA0 if properly configured

# Check if Bluetooth is disabled
dmesg | grep -i uart
# Should NOT show "hci_uart_bcm" if Bluetooth properly disabled

# Test UART directly
sudo cat /dev/ttyAMA0
# Should show NMEA sentences starting with $ if GPS working

# If no UART devices, add to /boot/firmware/config.txt:
echo "enable_uart=1" | sudo tee -a /boot/firmware/config.txt
echo "dtoverlay=disable-bt" | sudo tee -a /boot/firmware/config.txt
```

#### 2. OLED Display Not Working
```bash
# Check SPI is enabled
ls -la /dev/spi*

# Check for I2C devices
sudo i2cdetect -y 1

# Test in simulation mode
python3 software/main.py --simulate
```

#### 2. Service Won't Start
```bash
# Check service status
./service.sh status

# View detailed logs
sudo journalctl -u pi-rtk-surveyor --no-pager

# Check permissions
ls -la software/main.py
```

#### 3. Python Import Errors
```bash
# Reinstall dependencies
pip3 install --user -r install/requirements.txt

# Check Python path
python3 -c "import sys; print(sys.path)"
```

#### 4. GPIO Permission Issues
```bash
# Add user to gpio group (should be done by setup script)
sudo usermod -a -G gpio,spi,i2c pi

# Logout and login again
```

### Log Locations

```bash
# System service logs
sudo journalctl -u pi-rtk-surveyor

# Application logs  
tail -f data/logs/rtk_surveyor.log

# Installation logs
less install.log  # Created during setup
```

### Reset to Factory Settings

```bash
# Stop service
./service.sh stop

# Remove logs and data
rm -rf data/logs/*
rm -rf data/surveys/*

# Reset configuration
rm -f software/config/device_config.json

# Restart service
./service.sh start
```

## Development Mode

For development and testing:

### 1. Disable Auto-Start
```bash
./service.sh disable
./service.sh stop
```

### 2. Run in Development Mode
```bash
cd software
python3 main.py --simulate --debug
```

### 3. Live Development
```bash
# Edit code, then test immediately:
python3 main.py --simulate

# Or test specific components:
python3 display/oled_manager.py
python3 monitoring/system_monitor.py
```

## Performance Optimization

### Reduce Memory Usage
Edit service file to limit resources:
```bash
sudo systemctl edit pi-rtk-surveyor
```

Add:
```ini
[Service]
MemoryLimit=256M
CPUQuota=50%
```

### Faster Boot Times
```bash
# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable wifi-powersave@wlan0

# Remove desktop packages (if using Lite)
sudo apt remove --purge xserver* lightdm* desktop-base
```

## Next Steps

Once the basic system is running:

1. **Test OLED Display** - Verify splash screen and menus work
2. **Add GPS Module** - Connect and test LC29H GNSS HAT
3. **Implement Button Controls** - Add button input handling
4. **WiFi Configuration** - Set up RTK communication
5. **Field Testing** - Test with actual hardware stack

## Getting Help

- **Check Logs**: `./service.sh logs`
- **Test Mode**: `./test.sh` 
- **GitHub Issues**: Report problems with detailed logs
- **Hardware**: Verify connections and power supply

---

**Hardware working?** → Continue to [Button Integration Guide](button-integration.md)  
**Issues?** → Check troubleshooting section above 