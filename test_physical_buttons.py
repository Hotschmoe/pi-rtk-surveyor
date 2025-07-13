#!/usr/bin/env python3
"""
Physical Button Test Script
Tests the physical buttons on the Pi RTK Surveyor hardware
"""

import sys
import time
import logging
from pathlib import Path

# Add software directory to Python path
software_dir = Path(__file__).parent / "software"
sys.path.insert(0, str(software_dir))

from software.input.button_manager import ButtonManager, ButtonType, ButtonEvent

def test_physical_buttons():
    """Test physical button functionality"""
    print("Pi RTK Surveyor - Physical Button Test")
    print("=" * 40)
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create button manager in hardware mode (not simulation)
    print("Initializing button manager in hardware mode...")
    button_manager = ButtonManager(simulate_buttons=False)
    
    # Test callback function
    def button_callback(button, event):
        print(f">>> BUTTON EVENT: {button.value} {event.value} at {time.time():.3f}")
    
    # Register callbacks for all buttons
    print("Registering button callbacks...")
    for button in ButtonType:
        button_manager.register_callback(button, ButtonEvent.PRESS, button_callback)
        button_manager.register_callback(button, ButtonEvent.RELEASE, button_callback)
        button_manager.register_callback(button, ButtonEvent.LONG_PRESS, button_callback)
    
    # Start button monitoring
    print("Starting button monitoring...")
    button_manager.start()
    
    print("\nButton test ready!")
    print("Hardware buttons to test:")
    print("  KEY1 (GPIO 21) - Mode/Menu")
    print("  KEY2 (GPIO 20) - Settings/Brightness")
    print("  KEY3 (GPIO 16) - Action/Logging")
    print("  JOY_UP (GPIO 6) - Joystick Up")
    print("  JOY_DOWN (GPIO 19) - Joystick Down")
    print("  JOY_LEFT (GPIO 5) - Joystick Left")
    print("  JOY_RIGHT (GPIO 26) - Joystick Right")
    print("  JOY_PRESS (GPIO 13) - Joystick Press")
    print("\nPress any button to test...")
    print("Press Ctrl+C to stop")
    
    try:
        # Monitor for button events
        while True:
            # Check for queued events
            events = button_manager.get_button_events()
            if events:
                for event in events:
                    timestamp = event.get('timestamp', time.time())
                    print(f"Event Queue: {event['button'].value} {event['event'].value} at {timestamp:.3f}")
            
            # Small delay to prevent busy waiting
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopping button test...")
    finally:
        button_manager.stop()
        print("Button test complete!")

def check_gpio_status():
    """Check GPIO availability and status"""
    print("Checking GPIO status...")
    
    try:
        import RPi.GPIO as GPIO
        print("✓ RPi.GPIO module imported successfully")
        
        # Try to set GPIO mode
        GPIO.setmode(GPIO.BCM)
        print("✓ GPIO mode set to BCM")
        
        # Test a simple GPIO setup
        test_pin = 21  # KEY1
        GPIO.setup(test_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        initial_state = GPIO.input(test_pin)
        print(f"✓ GPIO {test_pin} (KEY1) initial state: {initial_state}")
        
        GPIO.cleanup()
        print("✓ GPIO cleanup successful")
        
        return True
        
    except ImportError:
        print("✗ RPi.GPIO module not available")
        return False
    except Exception as e:
        print(f"✗ GPIO error: {e}")
        return False

if __name__ == "__main__":
    print("Pi RTK Surveyor - Button Hardware Test")
    print("=" * 45)
    
    # Check GPIO first
    if check_gpio_status():
        print("\nGPIO hardware check passed!")
        print("Starting physical button test...\n")
        test_physical_buttons()
    else:
        print("\nGPIO hardware check failed!")
        print("Cannot test physical buttons without GPIO support")
        sys.exit(1) 