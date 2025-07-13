#!/usr/bin/env python3
"""
Button Manager for Pi RTK Surveyor
Handles Waveshare 1.3" OLED HAT button and joystick input
"""

import time
import threading
from typing import Dict, List, Callable, Optional
from enum import Enum
import logging

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO not available - using simulation mode")

class ButtonEvent(Enum):
    """Button event types"""
    PRESS = "press"
    RELEASE = "release"
    LONG_PRESS = "long_press"

class ButtonType(Enum):
    """Button types on Waveshare 1.3" OLED HAT"""
    KEY1 = "KEY1"
    KEY2 = "KEY2" 
    KEY3 = "KEY3"
    JOY_UP = "JOY_UP"
    JOY_DOWN = "JOY_DOWN"
    JOY_LEFT = "JOY_LEFT"
    JOY_RIGHT = "JOY_RIGHT"
    JOY_PRESS = "JOY_PRESS"

class ButtonManager:
    """Manages button input for Pi RTK Surveyor"""
    
    # GPIO pin mappings for Waveshare 1.3" OLED HAT
    BUTTON_PINS = {
        ButtonType.KEY1: 21,
        ButtonType.KEY2: 20,
        ButtonType.KEY3: 16,
        ButtonType.JOY_UP: 6,
        ButtonType.JOY_DOWN: 19,
        ButtonType.JOY_LEFT: 5,
        ButtonType.JOY_RIGHT: 26,
        ButtonType.JOY_PRESS: 13
    }
    
    def __init__(self, simulate_buttons: bool = False):
        """
        Initialize button manager
        
        Args:
            simulate_buttons: If True, uses keyboard simulation instead of GPIO
        """
        self.logger = logging.getLogger(__name__)
        
        # Check GPIO availability
        gpio_available = GPIO_AVAILABLE
        self.logger.info(f"GPIO availability check: {gpio_available}")
        
        # Override simulation if explicitly requested or if GPIO not available
        self.simulate_buttons = simulate_buttons or not gpio_available
        
        if simulate_buttons and gpio_available:
            self.logger.info("Hardware GPIO available but simulation mode requested")
        elif not gpio_available:
            self.logger.warning("GPIO not available - forced to simulation mode")
        else:
            self.logger.info("Hardware GPIO mode enabled")
        
        # Button state tracking
        self.button_states = {}
        self.button_press_times = {}
        self.event_callbacks = {}
        self.running = False
        
        # Timing constants
        self.debounce_time = 0.05  # 50ms debounce
        self.long_press_time = 1.0  # 1 second for long press
        
        # Threading
        self.monitor_thread = None
        self.event_queue = []
        self.queue_lock = threading.Lock()
        
        # Keyboard simulation mappings
        self.keyboard_mappings = {
            'k': ButtonType.KEY1,    # Mode selection
            'j': ButtonType.KEY2,    # Settings/brightness
            'l': ButtonType.KEY3,    # Action/logging
            'w': ButtonType.JOY_UP,
            's': ButtonType.JOY_DOWN,
            'a': ButtonType.JOY_LEFT,
            'd': ButtonType.JOY_RIGHT,
            ' ': ButtonType.JOY_PRESS
        }
        
        # Initialize hardware or simulation
        self._init_buttons()
        
    def _init_buttons(self):
        """Initialize button hardware or simulation"""
        if self.simulate_buttons:
            self.logger.info("Button manager initialized in simulation mode")
            self.logger.info("Keyboard mappings: k=KEY1, j=KEY2, l=KEY3, wasd=joystick, space=joy_press")
            # Initialize button states for simulation
            for button in ButtonType:
                self.button_states[button] = False
                self.button_press_times[button] = 0
        else:
            try:
                # Set up GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                # Configure button pins
                for button, pin in self.BUTTON_PINS.items():
                    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    self.button_states[button] = False
                    self.button_press_times[button] = 0
                    
                    # Set up interrupt for button press
                    GPIO.add_event_detect(pin, GPIO.BOTH, 
                                        callback=lambda pin, btn=button: self._gpio_callback(btn),
                                        bouncetime=int(self.debounce_time * 1000))
                
                self.logger.info("Button manager initialized with GPIO hardware")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize GPIO: {e}")
                self.simulate_buttons = True
                self.logger.info("Falling back to simulation mode")
    
    def start(self):
        """Start button monitoring"""
        if self.running:
            return
            
        self.running = True
        
        if self.simulate_buttons:
            # Start keyboard input thread for simulation
            self.monitor_thread = threading.Thread(target=self._keyboard_monitor, daemon=True)
            self.monitor_thread.start()
            
        self.logger.info("Button monitoring started")
    
    def stop(self):
        """Stop button monitoring"""
        self.running = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
            
        if not self.simulate_buttons and GPIO_AVAILABLE:
            try:
                GPIO.cleanup()
            except:
                pass
                
        self.logger.info("Button monitoring stopped")
    
    def register_callback(self, button: ButtonType, event: ButtonEvent, callback: Callable):
        """
        Register callback for button event
        
        Args:
            button: Button type
            event: Event type (press, release, long_press)
            callback: Function to call when event occurs
        """
        key = (button, event)
        if key not in self.event_callbacks:
            self.event_callbacks[key] = []
        self.event_callbacks[key].append(callback)
        
        self.logger.debug(f"Registered callback for {button.value} {event.value}")
    
    def unregister_callback(self, button: ButtonType, event: ButtonEvent, callback: Callable):
        """Remove callback for button event"""
        key = (button, event)
        if key in self.event_callbacks and callback in self.event_callbacks[key]:
            self.event_callbacks[key].remove(callback)
    
    def get_button_events(self) -> List[Dict]:
        """Get pending button events"""
        with self.queue_lock:
            events = self.event_queue.copy()
            self.event_queue.clear()
        return events
    
    def is_button_pressed(self, button: ButtonType) -> bool:
        """Check if button is currently pressed"""
        return self.button_states.get(button, False)
    
    def _gpio_callback(self, button: ButtonType):
        """GPIO interrupt callback"""
        if not self.running:
            return
            
        pin = self.BUTTON_PINS[button]
        current_state = not GPIO.input(pin)  # Inverted due to pull-up
        previous_state = self.button_states[button]
        
        if current_state != previous_state:
            self._handle_button_state_change(button, current_state)
    
    def _handle_button_state_change(self, button: ButtonType, pressed: bool):
        """Handle button state change"""
        current_time = time.time()
        
        if pressed:
            # Button pressed
            self.button_states[button] = True
            self.button_press_times[button] = current_time
            self._trigger_event(button, ButtonEvent.PRESS)
            
            # Start long press detection
            threading.Timer(self.long_press_time, 
                          self._check_long_press, 
                          args=[button, current_time]).start()
        else:
            # Button released
            if self.button_states[button]:  # Was previously pressed
                press_duration = current_time - self.button_press_times[button]
                self.button_states[button] = False
                self._trigger_event(button, ButtonEvent.RELEASE)
                
                # Don't trigger release if it was a long press
                if press_duration < self.long_press_time:
                    self.logger.debug(f"{button.value} short press: {press_duration:.3f}s")
    
    def _check_long_press(self, button: ButtonType, press_start_time: float):
        """Check if button is still pressed for long press detection"""
        if (self.button_states.get(button, False) and 
            self.button_press_times[button] == press_start_time):
            self._trigger_event(button, ButtonEvent.LONG_PRESS)
            self.logger.debug(f"{button.value} long press detected")
    
    def _trigger_event(self, button: ButtonType, event: ButtonEvent):
        """Trigger button event callbacks"""
        # Add to event queue
        with self.queue_lock:
            self.event_queue.append({
                'button': button,
                'event': event,
                'timestamp': time.time()
            })
        
        # Call registered callbacks
        key = (button, event)
        if key in self.event_callbacks:
            for callback in self.event_callbacks[key]:
                try:
                    callback(button, event)
                except Exception as e:
                    self.logger.error(f"Error in button callback: {e}")
    
    def _keyboard_monitor(self):
        """Monitor keyboard input for simulation mode"""
        if not self.simulate_buttons:
            return
            
        self.logger.info("Keyboard simulation ready. Use external triggers for button events.")
        self.logger.info("Button simulation is disabled in production mode.")
        
        # Keep thread alive but don't automatically press buttons
        while self.running:
            try:
                time.sleep(1)
                if not self.running:
                    break
                        
            except KeyboardInterrupt:
                break
                    
        self.logger.info("Keyboard monitor stopped")
    
    def _simulate_button_press(self, button: ButtonType):
        """Simulate a button press for testing"""
        if not self.running:
            return
            
        self.logger.info(f"Simulating {button.value} press")
        
        # Simulate press
        self._handle_button_state_change(button, True)
        
        # Simulate release after short delay
        threading.Timer(0.1, self._handle_button_state_change, 
                       args=[button, False]).start()
    
    def simulate_button_event(self, button: ButtonType, event: ButtonEvent = ButtonEvent.PRESS):
        """Manually simulate button event (for testing)"""
        if event == ButtonEvent.PRESS:
            self._simulate_button_press(button)
        elif event == ButtonEvent.LONG_PRESS:
            self._trigger_event(button, ButtonEvent.LONG_PRESS)
        else:
            self._trigger_event(button, event)


# Button action handlers for common operations
class ButtonActions:
    """Common button action handlers"""
    
    def __init__(self, app_context):
        """Initialize with application context"""
        self.app = app_context
        self.logger = logging.getLogger(__name__)
    
    def handle_key1_press(self, button: ButtonType, event: ButtonEvent):
        """Handle KEY1 press - Mode/Menu navigation"""
        self.logger.info("KEY1 pressed - Mode selection")
        if hasattr(self.app, 'cycle_display_mode'):
            self.app.cycle_display_mode()
    
    def handle_key2_press(self, button: ButtonType, event: ButtonEvent):
        """Handle KEY2 press - Settings/Brightness"""
        self.logger.info("KEY2 pressed - Settings")
        if hasattr(self.app, 'adjust_brightness'):
            self.app.adjust_brightness()
    
    def handle_key3_press(self, button: ButtonType, event: ButtonEvent):
        """Handle KEY3 press - Action/Logging"""
        self.logger.info("KEY3 pressed - Action button")
        if hasattr(self.app, 'toggle_logging'):
            self.app.toggle_logging()
    
    def handle_joystick_navigation(self, button: ButtonType, event: ButtonEvent):
        """Handle joystick navigation"""
        direction = button.value.replace('JOY_', '').lower()
        self.logger.info(f"Joystick {direction}")
        if hasattr(self.app, 'handle_navigation'):
            self.app.handle_navigation(direction)


# Test function for development
if __name__ == "__main__":
    import sys
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("Testing Button Manager...")
    
    # Create button manager in simulation mode
    button_manager = ButtonManager(simulate_buttons=True)
    
    # Test event callbacks
    def test_callback(button, event):
        print(f"Callback: {button.value} {event.value}")
    
    # Register test callbacks
    button_manager.register_callback(ButtonType.KEY1, ButtonEvent.PRESS, test_callback)
    button_manager.register_callback(ButtonType.KEY2, ButtonEvent.PRESS, test_callback)
    button_manager.register_callback(ButtonType.KEY3, ButtonEvent.PRESS, test_callback)
    
    # Start monitoring
    button_manager.start()
    
    print("Button manager started in simulation mode...")
    print("Simulated button presses will occur automatically...")
    print("Press Ctrl+C to stop")
    
    try:
        # Monitor for events
        while True:
            events = button_manager.get_button_events()
            for event in events:
                print(f"Event: {event['button'].value} {event['event'].value} at {event['timestamp']:.3f}")
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopping button manager...")
        button_manager.stop()
        print("Button manager test complete!")
