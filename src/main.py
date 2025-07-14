#!/usr/bin/env python3
"""
Pi RTK Surveyor Main Application
"""

import time
import logging
import signal
import sys
import threading
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
        self.display_mode = "splash"  # splash, menu, base_init, rover_init, base, rover, system
        self.device_role = None  # "base" or "rover"
        self.brightness_level = 255
        self.initialization_complete = False
        
        # Base station state
        self.rovers_connected = 0
        self.points_logged = 0
        self.webserver_running = False
        self.wifi_hotspot_running = False
        
        # Rover state
        self.base_connected = False
        self.signal_strength = 0
        self.point_logging_ready = False
        
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
                    
                    # Handle mode-specific operations
                    self._handle_mode_operations()
                    
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
            elif self.display_mode == "base":
                self._update_base_display()
            elif self.display_mode == "rover":
                self._update_rover_display()
                        
        except Exception as e:
            self.logger.error(f"Display update error: {e}")
    
    def _update_base_display(self):
        """Update display for base station mode"""
        if not self.initialization_complete:
            return
            
        # Get system info for monitoring
        if self.system_monitor:
            info = self.system_monitor.get_system_info()
            battery_level = info['battery_level']
            uptime = self._format_uptime(info['uptime'])
        else:
            battery_level = 0.0
            uptime = "0m"
        
        # Get GPS satellite count
        satellites = 0
        if self.gps_controller:
            position = self.gps_controller.get_position()
            if position and hasattr(position, 'satellites_used'):
                satellites = position.satellites_used
        
        if self.oled:
            self.oled.show_base_monitoring(
                satellites=satellites,
                rovers_connected=self.rovers_connected,
                battery_level=battery_level,
                uptime=uptime,
                points_logged=self.points_logged
            )
    
    def _update_rover_display(self):
        """Update display for rover mode"""
        if not self.initialization_complete:
            return
            
        # Get system info for monitoring
        if self.system_monitor:
            info = self.system_monitor.get_system_info()
            battery_level = info['battery_level']
            uptime = self._format_uptime(info['uptime'])
        else:
            battery_level = 0.0
            uptime = "0m"
        
        # Get GPS satellite count
        satellites = 0
        if self.gps_controller:
            position = self.gps_controller.get_position()
            if position and hasattr(position, 'satellites_used'):
                satellites = position.satellites_used
        
        if self.oled:
            self.oled.show_rover_monitoring(
                satellites=satellites,
                base_connected=self.base_connected,
                signal_strength=self.signal_strength,
                battery_level=battery_level,
                uptime=uptime,
                point_ready=self.point_logging_ready
            )
    
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
                self.display_mode = "base_init"
                self.initialization_complete = False
                self.logger.info("Device set to Base Station mode")
                # Start base initialization in background thread
                threading.Thread(target=self._initialize_base_station, daemon=True).start()
            elif button == ButtonType.KEY2:
                self.device_role = "rover"
                self.display_mode = "rover_init"
                self.initialization_complete = False
                self.logger.info("Device set to Rover mode")
                # Start rover initialization in background thread
                threading.Thread(target=self._initialize_rover, daemon=True).start()
            elif button == ButtonType.KEY3:
                self.display_mode = "system"
                self.logger.info("Switched to System Info mode")
    
    def _handle_operation_buttons(self, button, event_type):
        """Handle button events in operation mode"""
        from hardware.button_manager import ButtonType, ButtonEvent
        
        if event_type == ButtonEvent.PRESS:
            if button == ButtonType.KEY1:
                self.display_mode = "menu"
                self.device_role = None
                self.initialization_complete = False
                self.logger.info("Returned to menu")
            elif button == ButtonType.KEY2:
                self.adjust_brightness()
            elif button == ButtonType.KEY3:
                if self.device_role == "rover":
                    self.log_survey_point()
                else:
                    self.toggle_logging()
    
    def _initialize_base_station(self):
        """Initialize base station components"""
        self.logger.info("Starting base station initialization...")
        
        # Step 1: Show base splash
        if self.oled:
            self.oled.show_base_init_screen("1/3", "Base Station Mode")
        time.sleep(2)
        
        # Step 2: Initialize web server
        if self.oled:
            self.oled.show_base_init_screen("2/3", "Starting Web Server...")
        time.sleep(2)
        # TODO: Start actual web server
        self.webserver_running = True
        self.logger.info("Web server initialized (placeholder)")
        
        # Step 3: Initialize WiFi hotspot
        if self.oled:
            self.oled.show_base_init_screen("3/3", "Starting WiFi Hotspot...")
        time.sleep(2)
        # TODO: Start actual WiFi hotspot
        self.wifi_hotspot_running = True
        self.logger.info("WiFi hotspot initialized (placeholder)")
        
        # Initialization complete
        self.initialization_complete = True
        self.display_mode = "base"
        self.logger.info("Base station initialization complete")
    
    def _initialize_rover(self):
        """Initialize rover components"""
        self.logger.info("Starting rover initialization...")
        
        # Step 1: Show rover splash
        if self.oled:
            self.oled.show_rover_init_screen("1/2", "Rover Mode")
        time.sleep(2)
        
        # Step 2: Connect to base station
        if self.oled:
            self.oled.show_rover_init_screen("2/2", "Searching for base...")
        time.sleep(2)
        
        # Simulate finding base
        if self.oled:
            self.oled.show_rover_init_screen("2/2", "Base found! Connecting...")
        time.sleep(2)
        
        # TODO: Implement actual base connection
        self.base_connected = True
        self.signal_strength = 85  # Placeholder
        self.point_logging_ready = True
        self.logger.info("Connected to base station (placeholder)")
        
        # Initialization complete
        self.initialization_complete = True
        self.display_mode = "rover"
        self.logger.info("Rover initialization complete")
    
    def _handle_mode_operations(self):
        """Handle ongoing operations for current mode"""
        if self.device_role == "base" and self.initialization_complete:
            # Base station operations
            pass  # TODO: Monitor rovers, handle connections
            
        elif self.device_role == "rover" and self.initialization_complete:
            # Rover operations
            pass  # TODO: Monitor base connection, handle corrections
    
    def _update_gps(self):
        """Update GPS data"""
        if not self.gps_controller:
            return
            
        try:
            # GPS controller handles its own updates
            pass
        except Exception as e:
            self.logger.error(f"GPS update error: {e}")
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human readable format"""
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h{minutes}m"
        else:
            return f"{minutes}m"
    
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
    
    def log_survey_point(self):
        """Log a survey point (rover mode)"""
        if self.device_role == "rover" and self.point_logging_ready:
            self.points_logged += 1
            self.logger.info(f"Survey point logged: {self.points_logged}")
            # TODO: Implement actual point logging
    
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
