#!/usr/bin/env python3
"""
GPIO Pin Diagnostic Script
Tests each GPIO pin individually to identify button hardware issues
"""

import sys
import time
import signal

def signal_handler(sig, frame):
    print('\nCleaning up and exiting...')
    cleanup_gpio()
    sys.exit(0)

def cleanup_gpio():
    """Clean up GPIO resources"""
    try:
        import RPi.GPIO as GPIO
        GPIO.cleanup()
        print("GPIO cleanup completed")
    except:
        pass

def test_individual_pins():
    """Test each GPIO pin individually"""
    try:
        import RPi.GPIO as GPIO
    except ImportError:
        print("RPi.GPIO not available")
        return False
    
    # Pin mappings for Waveshare 1.3" OLED HAT
    button_pins = {
        'KEY1': 21,
        'KEY2': 20,
        'KEY3': 16,
        'JOY_UP': 6,
        'JOY_DOWN': 19,
        'JOY_LEFT': 5,
        'JOY_RIGHT': 26,
        'JOY_PRESS': 13
    }
    
    print("Testing individual GPIO pins...")
    print("=" * 40)
    
    try:
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Test each pin
        for button_name, pin in button_pins.items():
            print(f"\nTesting {button_name} (GPIO {pin}):")
            
            try:
                # Setup pin
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                
                # Read initial state
                initial_state = GPIO.input(pin)
                print(f"  Initial state: {initial_state} ({'HIGH' if initial_state else 'LOW'})")
                
                # Test edge detection
                try:
                    GPIO.add_event_detect(pin, GPIO.BOTH, bouncetime=50)
                    print(f"  ✓ Edge detection setup successful")
                    GPIO.remove_event_detect(pin)
                except Exception as e:
                    print(f"  ✗ Edge detection failed: {e}")
                
                # Test reading multiple times
                print(f"  Reading pin state 5 times:")
                for i in range(5):
                    state = GPIO.input(pin)
                    print(f"    Read {i+1}: {state}")
                    time.sleep(0.1)
                
            except Exception as e:
                print(f"  ✗ Pin setup failed: {e}")
        
        print(f"\n" + "=" * 40)
        print("Manual button test - press buttons to see state changes")
        print("Press Ctrl+C to stop")
        
        # Setup all pins for monitoring
        for button_name, pin in button_pins.items():
            try:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            except:
                pass
        
        # Monitor button states
        last_states = {}
        for button_name, pin in button_pins.items():
            try:
                last_states[button_name] = GPIO.input(pin)
            except:
                last_states[button_name] = None
        
        print("Initial button states:")
        for button_name, state in last_states.items():
            if state is not None:
                print(f"  {button_name}: {state} ({'HIGH' if state else 'LOW'})")
        
        print("\nMonitoring for button presses (state changes)...")
        
        while True:
            # Check for state changes
            current_states = {}
            for button_name, pin in button_pins.items():
                try:
                    current_states[button_name] = GPIO.input(pin)
                except:
                    current_states[button_name] = None
            
            # Check for changes
            for button_name in button_pins:
                if (current_states[button_name] is not None and 
                    last_states[button_name] is not None and
                    current_states[button_name] != last_states[button_name]):
                    
                    state = current_states[button_name]
                    action = "RELEASED" if state else "PRESSED"
                    print(f">>> {button_name} {action} (GPIO {button_pins[button_name]}): {state}")
            
            last_states = current_states
            time.sleep(0.01)  # Check every 10ms
            
    except KeyboardInterrupt:
        print("\nStopping GPIO test...")
    except Exception as e:
        print(f"GPIO test error: {e}")
    finally:
        cleanup_gpio()
        
    return True

if __name__ == "__main__":
    print("Pi RTK Surveyor - GPIO Pin Diagnostic")
    print("=" * 45)
    
    # Register signal handler for clean exit
    signal.signal(signal.SIGINT, signal_handler)
    
    print("This script will test each GPIO pin individually")
    print("to help diagnose button hardware issues.\n")
    
    # Test pins
    test_individual_pins()
    
    print("GPIO diagnostic complete!") 