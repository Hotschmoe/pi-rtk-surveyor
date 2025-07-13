#!/usr/bin/env python3
"""
GPIO Manager for Pi RTK Surveyor
Centralized GPIO resource management and coordination
"""

import logging
import threading
from typing import Dict, Set, Optional, Callable
from enum import Enum

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

class PinMode(Enum):
    """GPIO pin modes"""
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    SPI = "SPI"
    I2C = "I2C"
    UART = "UART"

class PinPull(Enum):
    """GPIO pin pull resistor settings"""
    NONE = "NONE"
    UP = "UP"
    DOWN = "DOWN"

class GPIOManager:
    """Centralized GPIO resource manager"""
    
    # Standard Raspberry Pi pin allocations
    RESERVED_PINS = {
        # Power pins
        1: "3.3V", 2: "5V", 4: "5V", 6: "GND", 9: "GND", 14: "GND",
        17: "3.3V", 20: "GND", 25: "GND", 30: "GND", 34: "GND", 39: "GND",
        
        # I2C pins (if enabled)
        3: "I2C1_SDA", 5: "I2C1_SCL",
        
        # SPI pins (if enabled)
        19: "SPI0_MOSI", 21: "SPI0_MISO", 23: "SPI0_SCLK", 24: "SPI0_CE0", 26: "SPI0_CE1",
        
        # UART pins (if enabled)
        8: "UART0_TXD", 10: "UART0_RXD"
    }
    
    # Waveshare 1.3" OLED HAT pin assignments
    OLED_PINS = {
        8: "OLED_CS",      # SPI CE0
        10: "OLED_MOSI",   # SPI MOSI  
        11: "OLED_SCLK",   # SPI SCLK
        24: "OLED_DC",     # Data/Command
        25: "OLED_RST"     # Reset
    }
    
    BUTTON_PINS = {
        21: "KEY1", 20: "KEY2", 16: "KEY3",
        6: "JOY_UP", 19: "JOY_DOWN", 5: "JOY_LEFT", 26: "JOY_RIGHT", 13: "JOY_PRESS"
    }
    
    def __init__(self):
        """Initialize GPIO manager"""
        self.logger = logging.getLogger(__name__)
        
        if not GPIO_AVAILABLE:
            self.logger.error("RPi.GPIO not available - cannot initialize GPIO manager")
            raise RuntimeError("GPIO hardware not available")
        
        # Pin allocation tracking
        self.allocated_pins: Dict[int, str] = {}  # pin -> component_name
        self.pin_modes: Dict[int, PinMode] = {}   # pin -> mode
        self.pin_callbacks: Dict[int, Callable] = {}  # pin -> callback
        
        # Component registration
        self.registered_components: Set[str] = set()
        
        # Thread safety
        self.lock = threading.Lock()
        
        # GPIO initialization state
        self.gpio_initialized = False
        
        self.logger.info("GPIO Manager initialized")
        
    def initialize_gpio(self) -> bool:
        """Initialize GPIO system"""
        if self.gpio_initialized:
            self.logger.debug("GPIO already initialized")
            return True
            
        try:
            with self.lock:
                # Set GPIO mode if not already set
                try:
                    GPIO.setmode(GPIO.BCM)
                    self.logger.debug("GPIO mode set to BCM")
                except RuntimeError as e:
                    if "mode has already been set" in str(e):
                        self.logger.debug("GPIO mode already set to BCM")
                    else:
                        raise e
                
                # Disable GPIO warnings 
                GPIO.setwarnings(False)
                
                self.gpio_initialized = True
                self.logger.info("GPIO system initialized successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to initialize GPIO: {e}")
            return False
    
    def register_component(self, component_name: str) -> bool:
        """Register a hardware component with the GPIO manager"""
        with self.lock:
            if component_name in self.registered_components:
                self.logger.warning(f"Component '{component_name}' already registered")
                return False
                
            self.registered_components.add(component_name)
            self.logger.info(f"Component '{component_name}' registered")
            return True
    
    def request_pin(self, pin: int, component_name: str, mode: PinMode, 
                   pull: PinPull = PinPull.NONE, description: str = "") -> bool:
        """Request exclusive access to a GPIO pin"""
        with self.lock:
            # Check if component is registered
            if component_name not in self.registered_components:
                self.logger.error(f"Component '{component_name}' not registered")
                return False
            
            # Check if pin is available
            if pin in self.allocated_pins:
                current_owner = self.allocated_pins[pin]
                if current_owner != component_name:
                    self.logger.error(f"Pin {pin} already allocated to '{current_owner}'")
                    return False
                else:
                    self.logger.debug(f"Pin {pin} already allocated to '{component_name}'")
                    return True
            
            # Check against reserved pins
            if pin in self.RESERVED_PINS:
                reserved_for = self.RESERVED_PINS[pin]
                if mode == PinMode.SPI and "SPI" in reserved_for:
                    pass  # SPI pins can be used for SPI
                elif mode == PinMode.I2C and "I2C" in reserved_for:
                    pass  # I2C pins can be used for I2C
                else:
                    self.logger.warning(f"Pin {pin} is reserved for {reserved_for} but requested for {mode.value}")
            
            # Configure the pin
            if not self._configure_pin(pin, mode, pull):
                self.logger.error(f"Failed to configure pin {pin} for mode {mode.value}")
                return False
            
            # Allocate the pin
            self.allocated_pins[pin] = component_name
            self.pin_modes[pin] = mode
            
            desc_str = f" ({description})" if description else ""
            self.logger.info(f"Pin {pin} allocated to '{component_name}'{desc_str}")
            return True
    
    def release_pin(self, pin: int, component_name: str) -> bool:
        """Release a GPIO pin"""
        with self.lock:
            if pin not in self.allocated_pins:
                self.logger.warning(f"Pin {pin} not allocated")
                return False
                
            if self.allocated_pins[pin] != component_name:
                self.logger.error(f"Pin {pin} not owned by '{component_name}'")
                return False
            
            # Clean up pin
            self._cleanup_pin(pin)
            
            # Remove from tracking
            del self.allocated_pins[pin]
            del self.pin_modes[pin]
            if pin in self.pin_callbacks:
                del self.pin_callbacks[pin]
            
            self.logger.info(f"Pin {pin} released by '{component_name}'")
            return True
    
    def request_button_pins(self, component_name: str) -> bool:
        """Request all button pins for a component"""
        success = True
        allocated_pins = []
        
        self.logger.info(f"Requesting button pins for component '{component_name}'")
        for pin, description in self.BUTTON_PINS.items():
            self.logger.debug(f"Attempting to allocate pin {pin} for {description}")
            if self.request_pin(pin, component_name, PinMode.INPUT, PinPull.UP, description):
                allocated_pins.append(pin)
                self.logger.debug(f"Successfully allocated pin {pin} for {description}")
            else:
                self.logger.error(f"Failed to allocate pin {pin} for {description}")
                success = False
                break
        
        if not success:
            self.logger.error(f"Button pin allocation failed for '{component_name}', cleaning up...")
            # Clean up any pins that were allocated
            for pin in allocated_pins:
                self.release_pin(pin, component_name)
            return False
        
        self.logger.info(f"All button pins successfully allocated for '{component_name}'")
        return True
    
    def request_oled_pins(self, component_name: str) -> bool:
        """Request OLED display pins for a component"""
        success = True
        allocated_pins = []
        
        for pin, description in self.OLED_PINS.items():
            # OLED pins are managed by luma.oled library via SPI
            mode = PinMode.SPI if pin in [8, 10, 11] else PinMode.OUTPUT
            if self.request_pin(pin, component_name, mode, PinPull.NONE, description):
                allocated_pins.append(pin)
            else:
                success = False
                break
        
        if not success:
            # Clean up any pins that were allocated
            for pin in allocated_pins:
                self.release_pin(pin, component_name)
            return False
        
        return True
    
    def setup_interrupt(self, pin: int, component_name: str, callback: Callable,
                       edge: str = "BOTH", bouncetime: int = 50) -> bool:
        """Set up GPIO interrupt for a pin"""
        with self.lock:
            if pin not in self.allocated_pins:
                self.logger.error(f"Pin {pin} not allocated")
                return False
                
            if self.allocated_pins[pin] != component_name:
                self.logger.error(f"Pin {pin} not owned by '{component_name}'")
                return False
            
            try:
                # Remove existing interrupt if any
                try:
                    GPIO.remove_event_detect(pin)
                except RuntimeError:
                    pass  # No existing interrupt
                
                # Set up new interrupt
                edge_map = {
                    "RISING": GPIO.RISING,
                    "FALLING": GPIO.FALLING,
                    "BOTH": GPIO.BOTH
                }
                
                GPIO.add_event_detect(pin, edge_map[edge], 
                                    callback=callback, bouncetime=bouncetime)
                
                self.pin_callbacks[pin] = callback
                self.logger.debug(f"Interrupt setup for pin {pin} ({edge})")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to setup interrupt for pin {pin}: {e}")
                return False
    
    def read_pin(self, pin: int) -> Optional[bool]:
        """Read GPIO pin state"""
        try:
            return bool(GPIO.input(pin))
        except Exception as e:
            self.logger.error(f"Error reading pin {pin}: {e}")
            return None
    
    def write_pin(self, pin: int, value: bool) -> bool:
        """Write GPIO pin state"""
        try:
            GPIO.output(pin, value)
            return True
        except Exception as e:
            self.logger.error(f"Error writing pin {pin}: {e}")
            return False
    
    def _configure_pin(self, pin: int, mode: PinMode, pull: PinPull) -> bool:
        """Configure a GPIO pin"""
        try:
            self.logger.debug(f"Configuring pin {pin} as {mode.value} with pull {pull.value}")
            
            if mode == PinMode.INPUT:
                pull_map = {
                    PinPull.NONE: GPIO.PUD_OFF,
                    PinPull.UP: GPIO.PUD_UP,
                    PinPull.DOWN: GPIO.PUD_DOWN
                }
                GPIO.setup(pin, GPIO.IN, pull_up_down=pull_map[pull])
                self.logger.debug(f"Pin {pin} configured as INPUT with pull {pull.value}")
                
            elif mode == PinMode.OUTPUT:
                GPIO.setup(pin, GPIO.OUT)
                self.logger.debug(f"Pin {pin} configured as OUTPUT")
                
            elif mode in [PinMode.SPI, PinMode.I2C, PinMode.UART]:
                # These are handled by their respective libraries
                # We just track them for conflict detection
                self.logger.debug(f"Pin {pin} marked as {mode.value} (managed by library)")
                pass
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure pin {pin}: {e}")
            return False
    
    def _cleanup_pin(self, pin: int):
        """Clean up a GPIO pin"""
        try:
            # Remove event detection if any
            try:
                GPIO.remove_event_detect(pin)
            except RuntimeError:
                pass  # No event detection set
                
        except Exception as e:
            self.logger.warning(f"Error cleaning up pin {pin}: {e}")
    
    def get_pin_info(self) -> Dict[str, str]:
        """Get information about allocated pins"""
        with self.lock:
            info = {}
            for pin, component in self.allocated_pins.items():
                mode = self.pin_modes.get(pin, PinMode.INPUT)
                info[f"Pin {pin}"] = f"{component} ({mode.value})"
            return info
    
    def unregister_component(self, component_name: str) -> bool:
        """Unregister a component and release all its pins"""
        with self.lock:
            if component_name not in self.registered_components:
                self.logger.warning(f"Component '{component_name}' not registered")
                return False
            
            # Release all pins owned by this component
            pins_to_release = [pin for pin, owner in self.allocated_pins.items() 
                             if owner == component_name]
            
            for pin in pins_to_release:
                self.release_pin(pin, component_name)
            
            self.registered_components.remove(component_name)
            self.logger.info(f"Component '{component_name}' unregistered")
            return True
    
    def shutdown(self):
        """Shutdown GPIO manager and cleanup resources"""
        with self.lock:
            self.logger.info("Shutting down GPIO manager...")
            
            # Unregister all components (this releases their pins)
            components_to_unregister = list(self.registered_components)
            for component in components_to_unregister:
                self.unregister_component(component)
            
            self.gpio_initialized = False
            self.logger.info("GPIO manager shutdown complete")


# Singleton instance
_gpio_manager_instance = None
_gpio_manager_lock = threading.Lock()

def get_gpio_manager() -> GPIOManager:
    """Get the singleton GPIO manager instance"""
    global _gpio_manager_instance
    
    with _gpio_manager_lock:
        if _gpio_manager_instance is None:
            _gpio_manager_instance = GPIOManager()
            _gpio_manager_instance.initialize_gpio()
        return _gpio_manager_instance 