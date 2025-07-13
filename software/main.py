#!/usr/bin/env python3
"""
Pi RTK Surveyor - Main Application Entry Point
Handles system startup, hardware initialization, and application flow
"""

import os
import sys
import time
import signal
import logging
import argparse
from pathlib import Path
from enum import Enum

# Add software directory to Python path
software_dir = Path(__file__).parent
sys.path.insert(0, str(software_dir))

# Import local modules
from display.oled_manager import OLEDManager
from monitoring.system_monitor import SystemMonitor
from input.button_api import ButtonAPI, ButtonType, ButtonEvent
from gnss.lc29h_controller import LC29HController, GNSSPosition, FixType

class DisplayMode(Enum):
    """Display modes for the application"""
    DEVICE_SELECTION = "device_selection"
    SYSTEM_INFO = "system_info"
    GPS_STATUS = "gps_status"
    BASE_STATUS = "base_status"
    ROVER_STATUS = "rover_status"

class DeviceMode(Enum):
    """Device operation modes"""
    MENU = "menu"
    BASE_STATION = "base_station"
    ROVER = "rover"

class RTKSurveyorApp:
    """Main application class for Pi RTK Surveyor"""
    
    def __init__(self, simulate_hardware: bool = False):
        """
        Initialize the RTK Surveyor application
        
        Args:
            simulate_hardware: If True, run without actual hardware (for development)
        """
        self.simulate_hardware = simulate_hardware
        self.running = False
        
        # Application state
        self.device_mode = DeviceMode.MENU
        self.display_mode = DisplayMode.DEVICE_SELECTION
        self.display_brightness = 255
        self.logging_enabled = False
        self.menu_selection = 0
        
        # Initialize components
        self.oled = None
        self.system_monitor = None
        self.button_api = None
        self.gps_controller = None
        
        # GPS data
        self.current_gps_position = None
        
        # Set up logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _setup_logging(self):
        """Set up logging configuration"""
        log_level = logging.DEBUG if self.simulate_hardware else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('data/logs/rtk_surveyor.log') if Path('data/logs').exists() else logging.NullHandler()
            ]
        )
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
        
    def startup(self):
        """Initialize and start the application"""
        self.logger.info("Starting Pi RTK Surveyor...")
        self.logger.info(f"Hardware simulation mode: {self.simulate_hardware}")
        
        try:
            # Initialize OLED display
            self.logger.info("Initializing OLED display...")
            self.oled = OLEDManager(simulate_display=self.simulate_hardware)
            
            # Show splash screen
            self.logger.info("Displaying splash screen...")
            self.oled.show_splash_screen(duration=3.0)
            
            # Initialize system monitor
            self.logger.info("Initializing system monitor...")
            self.system_monitor = SystemMonitor()
            
            # Initialize button API
            self.logger.info("Initializing button interface...")
            self.button_api = ButtonAPI(app_context=self, simulate_buttons=self.simulate_hardware)
            self.button_api.start()
            
            # Initialize GPS controller
            self.logger.info("Initializing GPS controller...")
            self.gps_controller = LC29HController(simulate=self.simulate_hardware)
            self.gps_controller.register_position_callback(self._gps_position_callback)
            if self.gps_controller.start():
                self.logger.info("GPS controller started successfully")
            else:
                self.logger.warning("GPS controller failed to start")
            
            # Application is now running
            self.running = True
            self.logger.info("Pi RTK Surveyor startup complete!")
            
            # Start main application loop
            self._main_loop()
            
        except Exception as e:
            self.logger.error(f"Startup failed: {e}")
            raise
            
    def _main_loop(self):
        """Main application loop"""
        self.logger.info("Entering main application loop...")
        
        try:
            # Start with device selection
            self.display_mode = DisplayMode.DEVICE_SELECTION
            last_display_update = time.time()
            
            while self.running:
                current_time = time.time()
                
                # Update display every second or when mode changes
                if current_time - last_display_update >= 1.0:
                    self._update_display()
                    last_display_update = current_time
                
                # Process button events
                self._process_button_events()
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
    
    def _update_display(self):
        """Update the OLED display based on current mode"""
        if not self.oled:
            return
            
        try:
            if self.display_mode == DisplayMode.DEVICE_SELECTION:
                self.oled.show_device_selection()
                
            elif self.display_mode == DisplayMode.SYSTEM_INFO:
                if self.system_monitor:
                    sys_info = self.system_monitor.get_system_info()
                    self.oled.show_system_info(
                        cpu_temp=sys_info.get('cpu_temp', 0),
                        memory_usage=sys_info.get('memory_percent', 0),
                        battery_level=sys_info.get('battery_level', 100)
                    )
                    
            elif self.display_mode == DisplayMode.GPS_STATUS:
                self._display_gps_status()
                
            elif self.display_mode == DisplayMode.BASE_STATUS:
                self._display_base_status()
                
            elif self.display_mode == DisplayMode.ROVER_STATUS:
                self._display_rover_status()
                
        except Exception as e:
            self.logger.error(f"Display update error: {e}")
    
    def _display_gps_status(self):
        """Display GPS status information"""
        if not self.oled:
            return
            
        if self.current_gps_position and self.current_gps_position.valid:
            fix_type_name = self.current_gps_position.fix_type.name.replace('_', ' ')
            self.oled.show_gps_status(
                fix_type=fix_type_name,
                lat=self.current_gps_position.latitude,
                lon=self.current_gps_position.longitude,
                accuracy=self.current_gps_position.accuracy_horizontal
            )
        else:
            self.oled.show_gps_status(
                fix_type="Acquiring...",
                lat=0, lon=0, accuracy=99.9
            )
    
    def _display_base_status(self):
        """Display base station status"""
        if not self.oled:
            return
            
        if self.current_gps_position and self.current_gps_position.valid:
            # For base station, show position accuracy and satellite count
            fix_type_name = self.current_gps_position.fix_type.name.replace('_', ' ')
            self.oled.show_gps_status(
                fix_type=f"BASE: {fix_type_name}",
                lat=self.current_gps_position.latitude,
                lon=self.current_gps_position.longitude,
                accuracy=self.current_gps_position.accuracy_horizontal
            )
        else:
            self.oled.show_gps_status(
                fix_type="BASE: Acquiring...",
                lat=0, lon=0, accuracy=99.9
            )
    
    def _display_rover_status(self):
        """Display rover status"""
        if not self.oled:
            return
            
        if self.current_gps_position and self.current_gps_position.valid:
            # For rover, emphasize RTK status
            fix_type_name = self.current_gps_position.fix_type.name.replace('_', ' ')
            if self.current_gps_position.fix_type == FixType.RTK_FIXED:
                status = "RTK FIXED"
            elif self.current_gps_position.fix_type == FixType.RTK_FLOAT:
                status = "RTK FLOAT"
            else:
                status = f"ROVER: {fix_type_name}"
                
            self.oled.show_gps_status(
                fix_type=status,
                lat=self.current_gps_position.latitude,
                lon=self.current_gps_position.longitude,
                accuracy=self.current_gps_position.accuracy_horizontal
            )
        else:
            self.oled.show_gps_status(
                fix_type="ROVER: No RTK",
                lat=0, lon=0, accuracy=99.9
            )
    
    def _process_button_events(self):
        """Process pending button events"""
        if not self.button_api:
            return
            
        events = self.button_api.get_pending_events()
        for event in events:
            button = event['button']
            event_type = event['event']
            
            if event_type == ButtonEvent.PRESS:
                self.logger.debug(f"Button pressed: {button.value}")
                # Additional event processing can be added here
    
    # Button action handlers (called by ButtonActions)
    def cycle_display_mode(self):
        """Cycle through display modes (KEY1)"""
        modes = list(DisplayMode)
        current_index = modes.index(self.display_mode)
        next_index = (current_index + 1) % len(modes)
        self.display_mode = modes[next_index]
        
        self.logger.info(f"Display mode changed to: {self.display_mode.value}")
        self._update_display()
    
    def adjust_brightness(self):
        """Adjust display brightness (KEY2)"""
        brightness_levels = [64, 128, 192, 255]
        current_index = brightness_levels.index(self.display_brightness) if self.display_brightness in brightness_levels else 3
        next_index = (current_index + 1) % len(brightness_levels)
        self.display_brightness = brightness_levels[next_index]
        
        if self.oled:
            self.oled.set_brightness(self.display_brightness)
        
        self.logger.info(f"Brightness adjusted to: {self.display_brightness}")
    
    def toggle_logging(self):
        """Toggle data logging (KEY3)"""
        self.logging_enabled = not self.logging_enabled
        status = "enabled" if self.logging_enabled else "disabled"
        self.logger.info(f"Data logging {status}")
        
        # TODO: Implement actual data logging functionality
    
    def handle_navigation(self, direction: str):
        """Handle joystick navigation"""
        self.logger.info(f"Navigation: {direction}")
        
        if self.display_mode == DisplayMode.DEVICE_SELECTION:
            if direction == "up":
                self.menu_selection = (self.menu_selection - 1) % 2
            elif direction == "down":
                self.menu_selection = (self.menu_selection + 1) % 2
            elif direction == "press":
                self._select_device_mode()
    
    def _select_device_mode(self):
        """Select device mode from menu"""
        if self.menu_selection == 0:
            self.device_mode = DeviceMode.BASE_STATION
            self.display_mode = DisplayMode.BASE_STATUS
            self.logger.info("Device mode: Base Station selected")
        elif self.menu_selection == 1:
            self.device_mode = DeviceMode.ROVER
            self.display_mode = DisplayMode.ROVER_STATUS
            self.logger.info("Device mode: Rover selected")
        
        self._update_display()
    
    def _gps_position_callback(self, position: GNSSPosition):
        """Handle GPS position updates"""
        self.current_gps_position = position
        
        # Log significant GPS events
        if position.valid:
            if position.fix_type == FixType.RTK_FIXED:
                self.logger.info(f"RTK Fixed: {position.latitude:.6f}, {position.longitude:.6f} (±{position.accuracy_horizontal:.2f}m)")
            elif position.fix_type == FixType.RTK_FLOAT:
                self.logger.info(f"RTK Float: {position.latitude:.6f}, {position.longitude:.6f} (±{position.accuracy_horizontal:.2f}m)")
    
    def get_gps_status(self) -> dict:
        """Get current GPS status for external access"""
        if self.gps_controller:
            stats = self.gps_controller.get_statistics()
            if self.current_gps_position:
                return {
                    **self.current_gps_position.to_dict(),
                    'statistics': stats
                }
            else:
                return {'valid': False, 'statistics': stats}
        return {'valid': False, 'statistics': {}}
    
    def shutdown(self):
        """Shutdown the application gracefully"""
        if not self.running:
            return
            
        self.logger.info("Shutting down Pi RTK Surveyor...")
        self.running = False
        
        # Clean up components
        if self.gps_controller:
            self.gps_controller.stop()
            self.gps_controller.disconnect()
            
        if self.button_api:
            self.button_api.stop()
            
        if self.oled:
            self.oled.clear_display()
            self.oled.stop_display_loop()
            
        if self.system_monitor:
            # Stop system monitor if it has cleanup methods
            pass
            
        self.logger.info("Shutdown complete")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Pi RTK Surveyor')
    parser.add_argument(
        '--simulate', 
        action='store_true',
        help='Run in simulation mode without hardware'
    )
    parser.add_argument(
        '--debug',
        action='store_true', 
        help='Enable debug logging'
    )
    parser.add_argument(
        '--mode',
        choices=['base', 'rover'],
        help='Set device mode directly'
    )
    
    args = parser.parse_args()
    
    # Adjust logging level if debug mode
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and start application
    app = RTKSurveyorApp(simulate_hardware=args.simulate)
    
    # Set device mode if specified
    if args.mode == 'base':
        app.device_mode = DeviceMode.BASE_STATION
        app.display_mode = DisplayMode.BASE_STATUS
    elif args.mode == 'rover':
        app.device_mode = DeviceMode.ROVER
        app.display_mode = DisplayMode.ROVER_STATUS
    
    try:
        app.startup()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Application failed: {e}")
        sys.exit(1)
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
