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

from .gpio_manager import get_gpio_manager, PinMode, PinPull

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
    
    def __init__(self):
        """Initialize button manager"""
        self.logger = logging.getLogger(__name__)
        
        # Get GPIO manager instance
        self.gpio_manager = get_gpio_manager()
        
        # Component name for GPIO manager
        self.component_name = "button_manager"
        
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
        
        # Initialize hardware
        self._init_buttons()
        
    def _init_buttons(self):
        """Initialize button hardware"""
        try:
            # Register with GPIO manager
            if not self.gpio_manager.register_component(self.component_name):
                self.logger.error("Failed to register with GPIO manager")
                raise RuntimeError("Button manager registration failed")
            
            # Request all button pins through GPIO manager
            if not self.gpio_manager.request_button_pins(self.component_name):
                self.logger.error("Failed to allocate button pins")
                raise RuntimeError("Button pin allocation failed")
            
            # Set up interrupts for each button
            for button, pin in self.BUTTON_PINS.items():
                # Create callback function with proper closure
                def make_callback(btn):
                    return lambda pin_num: self._gpio_callback(btn)
                
                # Set up interrupt through GPIO manager
                if not self.gpio_manager.setup_interrupt(
                    pin, self.component_name, make_callback(button),
                    edge="BOTH", bouncetime=int(self.debounce_time * 1000)
                ):
                    self.logger.error(f"Failed to setup interrupt for {button.value}")
                    continue
                
                # Initialize button state
                self.button_states[button] = False
                self.button_press_times[button] = 0
            
            self.logger.info("Button manager initialized with GPIO hardware")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize GPIO buttons: {e}")
            raise RuntimeError(f"Button hardware initialization failed: {e}")
    
    def start(self):
        """Start button monitoring"""
        if self.running:
            return
            
        self.running = True
        self.logger.info("Button monitoring started")
    
    def stop(self):
        """Stop button monitoring"""
        self.running = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
            
        # Unregister from GPIO manager (this releases all pins)
        self.gpio_manager.unregister_component(self.component_name)
        self.logger.info("Button manager stopped")
    
    def register_callback(self, button: ButtonType, event: ButtonEvent, callback: Callable):
        """Register callback for button event"""
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
        
        # Read pin state through GPIO manager
        pin_state = self.gpio_manager.read_pin(pin)
        if pin_state is None:
            self.logger.warning(f"Failed to read pin {pin} for {button.value}")
            return
            
        current_state = not pin_state  # Inverted due to pull-up
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
