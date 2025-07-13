#!/usr/bin/env python3
"""
Pi RTK Surveyor Main Application
"""

import time
import logging
import signal
import sys
from typing import Optional

from hardware.gpio_manager import get_gpio_manager
from hardware.oled_manager import OLEDManager
from hardware.button_api import ButtonAPI
from hardware.system_monitor import SystemMonitor
from common.lc29h_controller import LC29HController


class PiRTKSurveyor:
    """Main application class for Pi RTK Surveyor"""
    
    def __init__(self):
        """Initialize the Pi RTK Surveyor application"""
        self.running = False
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize GPIO manager first
        try:
            self.gpio_manager = get_gpio_manager()
        except RuntimeError as e:
            self.logger.error(f"GPIO initialization failed: {e}")
            raise
        
        # Hardware components
        self.oled: Optional[OLEDManager] = None
        self.button_api: Optional[ButtonAPI] = None
        self.system_monitor: Optional[SystemMonitor] = None
        self.gps_controller: Optional[LC29HController] = None
        
        # Application state
        self.display_mode = "splash"  # splash, menu, base, rover, system
        self.device_role = None  # "base" or "rover"
        self.brightness_level = 255
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.logger.info("Pi RTK Surveyor initialized")
    
    def initialize_hardware(self) -> bool:
        """Initialize all hardware components"""
        try:
            self.logger.info("Initializing hardware components...")
            
            # Initialize system monitor first (no GPIO dependencies)
            self.system_monitor = SystemMonitor()
            self.logger.info("System monitor initialized")
            
            # Initialize OLED display
            self.oled = OLEDManager()
            self.logger.info("OLED display initialized")
            
            # Initialize button API
            self.button_api = ButtonAPI(app_context=self)
            self.logger.info("Button API initialized")
            
            # Initialize GPS controller
            self.gps_controller = LC29HController()
            self.logger.info("GPS controller initialized")
            
            # Show GPIO pin allocations
            pin_info = self.gpio_manager.get_pin_info()
            if pin_info:
                self.logger.info("GPIO pin allocations:")
                for pin, allocation in pin_info.items():
                    self.logger.info(f"  {pin}: {allocation}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Hardware initialization failed: {e}")
            return False
    
    def run(self):
        """Run the main application"""
        self.logger.info("Starting Pi RTK Surveyor...")
        
        # Initialize hardware
        if not self.initialize_hardware():
            self.logger.error("Failed to initialize hardware")
            return 1
        
        # Start hardware components
        if self.button_api:
            self.button_api.start()
        
        if self.gps_controller:
            self.gps_controller.start()
        
        # Show splash screen
        if self.oled:
            self.oled.show_splash_screen(duration=3.0)
            # Switch to menu mode after splash
            self.display_mode = "menu"
        
        # Main application loop
        self.running = True
        self.logger.info("Pi RTK Surveyor started successfully")
        
        try:
            while self.running:
                try:
                    # Update display based on current mode
                    self._update_display()
                    
                    # Process button events
                    self._process_button_events()
                    
                    # Update GPS data
                    self._update_gps()
                    
                    # Small delay to prevent busy waiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                    time.sleep(1)  # Prevent rapid error loops
                    
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested by user")
        finally:
            self.shutdown()
            
        return 0
    
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _update_display(self):
        """Update the OLED display based on current mode"""
        if not self.oled:
            return
            
        try:
            if self.display_mode == "menu":
                self.oled.show_device_selection()
            elif self.display_mode == "system":
                if self.system_monitor:
                    info = self.system_monitor.get_system_info()
                    self.oled.show_system_info(
                        cpu_temp=info['cpu_temp'],
                        memory_usage=info['memory_percent'],
                        battery_level=info['battery_level']
                    )
            elif self.display_mode in ["base", "rover"]:
                if self.gps_controller:
                    # Use the correct method name from LC29HController
                    gps_position = self.gps_controller.get_position()
                    if gps_position and gps_position.valid:
                        self.oled.show_gps_status(
                            fix_type=gps_position.fix_type.name.replace('_', ' '),
                            lat=gps_position.latitude,
                            lon=gps_position.longitude,
                            accuracy=gps_position.accuracy_horizontal
                        )
                    else:
                        self.oled.show_gps_status("No GPS Data", 0.0, 0.0, 99.9)
                        
        except Exception as e:
            self.logger.error(f"Display update error: {e}")
    
    def _process_button_events(self):
        """Process button events from the button API"""
        if not self.button_api:
            return
            
        try:
            events = self.button_api.get_pending_events()
            for event in events:
                button = event['button']
                event_type = event['event']
                
                self.logger.debug(f"Button event: {button.value} {event_type.value}")
                
                # Handle button events based on current mode
                if self.display_mode == "menu":
                    self._handle_menu_buttons(button, event_type)
                elif self.display_mode in ["base", "rover"]:
                    self._handle_operation_buttons(button, event_type)
                    
        except Exception as e:
            self.logger.error(f"Button processing error: {e}")
    
    def _handle_menu_buttons(self, button, event_type):
        """Handle button events in menu mode"""
        from hardware.button_manager import ButtonType, ButtonEvent
        
        if event_type == ButtonEvent.PRESS:
            if button == ButtonType.KEY1:
                self.device_role = "base"
                self.display_mode = "base"
                self.logger.info("Device set to Base Station mode")
            elif button == ButtonType.KEY2:
                self.device_role = "rover"
                self.display_mode = "rover"
                self.logger.info("Device set to Rover mode")
            elif button == ButtonType.KEY3:
                self.display_mode = "system"
                self.logger.info("Switched to System Info mode")
    
    def _handle_operation_buttons(self, button, event_type):
        """Handle button events in operation mode"""
        from hardware.button_manager import ButtonType, ButtonEvent
        
        if event_type == ButtonEvent.PRESS:
            if button == ButtonType.KEY1:
                self.display_mode = "menu"
                self.logger.info("Returned to menu")
            elif button == ButtonType.KEY2:
                self.adjust_brightness()
            elif button == ButtonType.KEY3:
                self.toggle_logging()
    
    def _update_gps(self):
        """Update GPS data"""
        if not self.gps_controller:
            return
            
        try:
            # GPS controller handles its own updates
            pass
        except Exception as e:
            self.logger.error(f"GPS update error: {e}")
    
    def cycle_display_mode(self):
        """Cycle through display modes"""
        modes = ["menu", "system", "base", "rover"]
        current_index = modes.index(self.display_mode) if self.display_mode in modes else 0
        next_index = (current_index + 1) % len(modes)
        self.display_mode = modes[next_index]
        self.logger.info(f"Display mode changed to: {self.display_mode}")
    
    def adjust_brightness(self):
        """Adjust display brightness"""
        brightness_levels = [64, 128, 192, 255]
        current_index = brightness_levels.index(self.brightness_level) if self.brightness_level in brightness_levels else 0
        next_index = (current_index + 1) % len(brightness_levels)
        self.brightness_level = brightness_levels[next_index]
        
        if self.oled and self.oled.device:
            self.oled.device.contrast(self.brightness_level)
            
        self.logger.info(f"Brightness adjusted to: {self.brightness_level}")
    
    def toggle_logging(self):
        """Toggle logging state"""
        # This would start/stop survey logging
        self.logger.info("Logging toggled")
    
    def handle_navigation(self, direction: str):
        """Handle joystick navigation"""
        self.logger.info(f"Navigation: {direction}")
        # Handle menu navigation, map panning, etc.
    
    def shutdown(self):
        """Shutdown the application gracefully"""
        if not self.running:
            return
            
        self.logger.info("Shutting down Pi RTK Surveyor...")
        self.running = False
        
        # Clean up components in reverse order of initialization
        # Stop button monitoring first to avoid GPIO conflicts
        if self.button_api:
            self.button_api.stop()
            self.logger.info("Button API stopped")
            
        if self.gps_controller:
            self.gps_controller.stop()
            self.gps_controller.disconnect()
            self.logger.info("GPS controller stopped")
            
        # Clean up OLED display
        if self.oled:
            self.oled.cleanup()
            self.logger.info("OLED display cleaned up")
        
        # Shutdown GPIO manager last
        if self.gpio_manager:
            self.gpio_manager.shutdown()
            self.logger.info("GPIO manager shutdown")
        
        self.logger.info("Shutdown complete")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pi RTK Surveyor')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Set logging level')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/tmp/pi-rtk-surveyor.log')
        ]
    )
    
    # Create and run application
    try:
        app = PiRTKSurveyor()
        return app.run()
    except Exception as e:
        logging.error(f"Application startup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
