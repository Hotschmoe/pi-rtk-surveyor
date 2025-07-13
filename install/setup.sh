#!/bin/bash
# Pi RTK Surveyor Installation Script
# This script sets up the Pi RTK Surveyor software on a Raspberry Pi

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(pwd)"
SERVICE_NAME="pi-rtk-surveyor"
USER="$(whoami)"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Pi RTK Surveyor Installation Script${NC}"
echo -e "${BLUE}================================================${NC}"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}Error: This script should not be run as root${NC}"
   echo "Please run as your regular user:"
   echo "  bash install/setup.sh"
   exit 1
fi

# Check if we're on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    echo "Some hardware-specific features may not work properly."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}Step 1: Updating system packages...${NC}"
sudo apt update
sudo apt upgrade -y

echo -e "${GREEN}Step 2: Installing system dependencies...${NC}"
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    i2c-tools \
    spi-tools \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7 \
    libtiff6

echo -e "${GREEN}Step 3: Enabling SPI and I2C interfaces...${NC}"
echo "SPI and I2C must be enabled for the OLED display to work."
echo "Please run the following command after installation:"
echo -e "${BLUE}sudo raspi-config${NC}"
echo "Navigate to: Interface Options > SPI > Enable"
echo "Navigate to: Interface Options > I2C > Enable"
echo "Then reboot when prompted."
echo
echo -e "${YELLOW}Note: The installation will continue, but hardware won't work until you enable SPI/I2C.${NC}"

echo -e "${GREEN}Step 4: Creating project directories...${NC}"
mkdir -p "${PROJECT_DIR}/data/logs"
mkdir -p "${PROJECT_DIR}/data/surveys"
mkdir -p "${PROJECT_DIR}/data/config"

echo -e "${GREEN}Step 5: Installing Python dependencies...${NC}"

# Install available packages via apt (system packages)
echo "Installing system Python packages..."
sudo apt install -y \
    python3-pil \
    python3-psutil \
    python3-yaml \
    python3-serial \
    python3-flask \
    python3-pytest \
    python3-gpiozero \
    python3-rpi.gpio \
    python3-full

# Create virtual environment for packages not available in apt
echo "Creating virtual environment for remaining packages..."
python3 -m venv "${PROJECT_DIR}/venv"

# Install remaining packages in virtual environment
echo "Installing packages in virtual environment..."
"${PROJECT_DIR}/venv/bin/pip" install \
    luma.oled>=3.12.0 \
    configparser>=5.3.0 \
    colorlog>=6.7.0 \
    pynmea2>=1.19.0 \
    flask-cors>=4.0.0 \
    flask-socketio>=5.3.0 \
    python-wifi>=0.6.1

echo -e "${GREEN}Step 6: Setting up systemd service...${NC}"
# Copy service file to systemd directory and replace placeholders
cp "${PROJECT_DIR}/install/systemd/${SERVICE_NAME}.service" "/tmp/${SERVICE_NAME}.service"

# Replace placeholders with actual values
sed -i "s|PLACEHOLDER_USER|${USER}|g" "/tmp/${SERVICE_NAME}.service"
sed -i "s|PLACEHOLDER_PROJECT_DIR|${PROJECT_DIR}|g" "/tmp/${SERVICE_NAME}.service"

# Copy to systemd directory
sudo mv "/tmp/${SERVICE_NAME}.service" "/etc/systemd/system/"

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}.service"

echo -e "${GREEN}Step 7: Setting up permissions...${NC}"
# Make scripts executable
chmod +x "${PROJECT_DIR}/software/main.py"
chmod +x "${PROJECT_DIR}/install/setup.sh"

# Add user to necessary groups
sudo usermod -a -G spi,i2c,gpio $USER

echo -e "${GREEN}Step 8: Creating helper scripts...${NC}"

# Create start script
cat > "${PROJECT_DIR}/start.sh" << EOF
#!/bin/bash
# Start Pi RTK Surveyor manually
cd ${PROJECT_DIR}/software
${PROJECT_DIR}/venv/bin/python main.py
EOF

# Create test script
cat > "${PROJECT_DIR}/test.sh" << EOF
#!/bin/bash
# Test Pi RTK Surveyor in simulation mode
cd ${PROJECT_DIR}/software
${PROJECT_DIR}/venv/bin/python main.py --simulate --debug
EOF

# Create service management script
cat > "${PROJECT_DIR}/service.sh" << 'EOF'
#!/bin/bash
# Pi RTK Surveyor service management

case "$1" in
    start)
        sudo systemctl start pi-rtk-surveyor
        echo "Service started"
        ;;
    stop)
        sudo systemctl stop pi-rtk-surveyor
        echo "Service stopped"
        ;;
    restart)
        sudo systemctl restart pi-rtk-surveyor
        echo "Service restarted"
        ;;
    status)
        sudo systemctl status pi-rtk-surveyor
        ;;
    logs)
        sudo journalctl -u pi-rtk-surveyor -f
        ;;
    enable)
        sudo systemctl enable pi-rtk-surveyor
        echo "Service enabled for auto-start"
        ;;
    disable)
        sudo systemctl disable pi-rtk-surveyor
        echo "Service disabled from auto-start"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|enable|disable}"
        exit 1
        ;;
esac
EOF

chmod +x "${PROJECT_DIR}/start.sh"
chmod +x "${PROJECT_DIR}/test.sh"
chmod +x "${PROJECT_DIR}/service.sh"

echo -e "${GREEN}Step 9: Testing installation...${NC}"
echo "Running quick test..."
cd "${PROJECT_DIR}/software"
timeout 10s "${PROJECT_DIR}/venv/bin/python" main.py --simulate || true

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ Installation completed successfully!${NC}"
echo -e "${BLUE}================================================${NC}"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Enable SPI and I2C interfaces:"
echo -e "   ${BLUE}sudo raspi-config${NC}"
echo "   Interface Options > SPI > Enable"
echo "   Interface Options > I2C > Enable"
echo
echo "2. Reboot when prompted by raspi-config"
echo
echo "3. After reboot, the service will start automatically with hardware support"
echo
echo -e "${YELLOW}Manual control:${NC}"
echo "• Test in simulation mode:"
echo -e "   ${BLUE}./test.sh${NC}"
echo
echo "• Start manually:"
echo -e "   ${BLUE}./start.sh${NC}"
echo
echo "• Service management:"
echo -e "   ${BLUE}./service.sh status${NC}    # Check service status"
echo -e "   ${BLUE}./service.sh logs${NC}      # View logs"
echo -e "   ${BLUE}./service.sh stop${NC}      # Stop service"
echo -e "   ${BLUE}./service.sh start${NC}     # Start service"
echo
echo -e "${YELLOW}Troubleshooting:${NC}"
echo "• Check hardware connections"
echo "• View logs: ./service.sh logs"
echo "• Test simulation mode: ./test.sh"
echo
echo -e "${GREEN}Installation complete!${NC}"
