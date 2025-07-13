#!/bin/bash
# Deploy and Test Physical Buttons Script
# For Pi RTK Surveyor hardware testing

echo "Pi RTK Surveyor - Deploy and Test Physical Buttons"
echo "=================================================="

# Check if running on Pi
if ! command -v gpio &> /dev/null; then
    echo "WARNING: This script is designed for Raspberry Pi hardware"
    echo "gpio command not found - you may not be on a Pi"
fi

# Check if we're in the right directory
if [ ! -f "software/main.py" ]; then
    echo "ERROR: Please run this script from the pi-rtk-surveyor directory"
    exit 1
fi

# Function to test GPIO availability
test_gpio() {
    echo "Testing GPIO availability..."
    python3 -c "
import sys
try:
    import RPi.GPIO as GPIO
    print('✓ RPi.GPIO module available')
    GPIO.setmode(GPIO.BCM)
    print('✓ GPIO mode set successfully')
    GPIO.cleanup()
    print('✓ GPIO cleanup successful')
    sys.exit(0)
except ImportError:
    print('✗ RPi.GPIO module not available')
    sys.exit(1)
except Exception as e:
    print(f'✗ GPIO error: {e}')
    sys.exit(1)
"
    return $?
}

# Function to stop the service
stop_service() {
    echo "Stopping pi-rtk-surveyor service..."
    sudo systemctl stop pi-rtk-surveyor.service
    echo "Service stopped."
}

# Function to start the service
start_service() {
    echo "Starting pi-rtk-surveyor service..."
    sudo systemctl start pi-rtk-surveyor.service
    echo "Service started."
}

# Function to test physical buttons
test_buttons() {
    echo "Testing physical buttons..."
    echo "This will run a dedicated button test script"
    echo "Press Ctrl+C to stop the test"
    echo ""
    
    # Make sure the test script is executable
    chmod +x test_physical_buttons.py
    
    # Run the button test
    python3 test_physical_buttons.py
}

# Function to run GPIO diagnostic
gpio_diagnostic() {
    echo "Running GPIO pin diagnostic..."
    echo "This will test each GPIO pin individually"
    echo "Press Ctrl+C to stop the test"
    echo ""
    
    # Make sure the diagnostic script is executable
    chmod +x debug_gpio_pins.py
    
    # Run the GPIO diagnostic
    python3 debug_gpio_pins.py
}

# Function to run main app without service
run_main_app() {
    echo "Running main application in hardware mode..."
    echo "This will run the main app directly (not as a service)"
    echo "Press Ctrl+C to stop"
    echo ""
    
    cd software
    python3 main.py --debug
}

# Function to check service logs
check_logs() {
    echo "Checking service logs for button events..."
    echo "Last 50 lines of service logs:"
    echo "=============================="
    sudo journalctl -u pi-rtk-surveyor.service -n 50 --no-pager
    echo ""
    echo "To follow logs in real-time, use:"
    echo "sudo journalctl -u pi-rtk-surveyor.service -f"
}

# Main menu
show_menu() {
    echo ""
    echo "Choose an option:"
    echo "1. Test GPIO availability"
    echo "2. Test physical buttons (dedicated test)"
    echo "3. GPIO pin diagnostic (individual pin test)"
    echo "4. Run main app directly (hardware mode)"
    echo "5. Stop service"
    echo "6. Start service"
    echo "7. Check service logs"
    echo "8. Exit"
    echo ""
    read -p "Enter your choice (1-8): " choice
}

# Main loop
while true; do
    show_menu
    case $choice in
        1)
            test_gpio
            if [ $? -eq 0 ]; then
                echo "GPIO test passed! Hardware buttons should work."
            else
                echo "GPIO test failed! Hardware buttons may not work."
            fi
            ;;
        2)
            stop_service
            test_buttons
            ;;
        3)
            stop_service
            gpio_diagnostic
            ;;
        4)
            stop_service
            run_main_app
            ;;
        5)
            stop_service
            ;;
        6)
            start_service
            ;;
        7)
            check_logs
            ;;
        8)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid option. Please choose 1-8."
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
done 