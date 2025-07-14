#!/usr/bin/env python3
"""
RTK Rover Implementation
Handles all rover operations including base connection and point logging
"""

import time
import logging
import signal
import sys
import threading
from typing import Optional
from pathlib import Path

# Add src directory to Python path for imports
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from hardware.oled_manager import OLEDManager
from hardware.button_api import ButtonAPI
from hardware.system_monitor import SystemMonitor
from hardware.gpio_manager import GPIOManager
from common.lc29h_controller import LC29HController


class RTKRover:
    """RTK Rover - handles all rover operations"""
    
    def __init__(self, oled_manager: Optional[OLEDManager] = None,
                 system_monitor: Optional[SystemMonitor] = None,
                 gps_controller: Optional[LC29HController] = None,
                 gpio_manager: Optional[GPIOManager] = None):
        """
        Initialize RTK Rover
        
        Args:
            oled_manager: OLED display manager from bootloader
            system_monitor: System monitor from bootloader
            gps_controller: GPS controller from bootloader
            gpio_manager: GPIO manager from bootloader
        """
        self.running = False
        self.initialization_complete = False
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Hardware components from bootloader
        self.oled = oled_manager
        self.system_monitor = system_monitor
        self.gps_controller = gps_controller
        self.gpio_manager = gpio_manager
        
        # Rover specific components
        self.button_api: Optional[ButtonAPI] = None
        
        # Rover state
        self.base_connected = False
        self.signal_strength = 0
        self.point_logging_ready = False
        self.points_logged = 0
        
        # Monitoring data
        self.satellites_count = 0
        self.rtk_status = "Initializing"
        self.current_position = None
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.logger.info("RTK Rover initialized")
    
    def run(self) -> int:
        """Run the rover"""
        self.logger.info("Starting RTK Rover...")
        
        # Initialize rover specific components
        if not self._initialize_rover_components():
            self.logger.error("Failed to initialize rover components")
            return 1
        
        # Start initialization sequence
        if not self._run_initialization_sequence():
            self.logger.error("Rover initialization failed")
            return 1
        
        # Main rover loop
        self.running = True
        self.initialization_complete = True
        self.logger.info("RTK Rover operational")
        
        try:
            while self.running:
                try:
                    # Update display
                    self._update_display()
                    
                    # Process button events
                    self._process_button_events()
                    
                    # Update monitoring data
                    self._update_monitoring_data()
                    
                    # Handle rover operations
                    self._handle_rover_operations()
                    
                    # Small delay to prevent busy waiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.logger.error(f"Error in rover loop: {e}")
                    time.sleep(1)  # Prevent rapid error loops
                    
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested by user")
        finally:
            self.shutdown()
            
        return 0
    
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        self.logger.info(f"Received signal {signum}, shutting down rover...")
        self.running = False
    
    def _initialize_rover_components(self) -> bool:
        """Initialize rover specific components"""
        try:
            # Initialize button API for rover operations
            self.button_api = ButtonAPI(app_context=self)
            self.button_api.start()
            self.logger.info("Rover button API initialized")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize rover components: {e}")
            return False
    
    def _run_initialization_sequence(self) -> bool:
        """Run the rover initialization sequence with display updates"""
        try:
            # Step 1: Show rover splash
            self.logger.info("Rover initialization sequence started")
            if self.oled:
                self.oled.show_rover_init_screen("1/2", "Rover Mode")
            time.sleep(2)
            
            # Step 2: Connect to base station
            if self.oled:
                self.oled.show_rover_init_screen("2/2", "Searching for base...")
            time.sleep(2)
            
            # Simulate searching and finding base
            if self.oled:
                self.oled.show_rover_init_screen("2/2", "Base found! Connecting...")
            time.sleep(2)
            
            # TODO: Implement actual base station connection
            self.base_connected = True
            self.signal_strength = 85  # Placeholder signal strength
            self.point_logging_ready = True
            self.logger.info("Connected to base station (placeholder)")
            
            self.logger.info("Rover initialization sequence complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization sequence failed: {e}")
            return False
    
    def _update_display(self):
        """Update the OLED display with rover monitoring info"""
        if not self.oled or not self.initialization_complete:
            return
            
        try:
            # Get system info for monitoring
            if self.system_monitor:
                info = self.system_monitor.get_system_info()
                battery_level = info['battery_level']
                uptime = self._format_uptime(info['uptime'])
            else:
                battery_level = 0.0
                uptime = "0m"
            
            self.oled.show_rover_monitoring(
                satellites=self.satellites_count,
                base_connected=self.base_connected,
                signal_strength=self.signal_strength,
                battery_level=battery_level,
                uptime=uptime,
                point_ready=self.point_logging_ready
            )
                        
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
                self._handle_rover_button_events(button, event_type)
                    
        except Exception as e:
            self.logger.error(f"Button processing error: {e}")
    
    def _handle_rover_button_events(self, button, event_type):
        """Handle button events in rover mode"""
        from hardware.button_manager import ButtonType, ButtonEvent
        
        if event_type == ButtonEvent.PRESS:
            if button == ButtonType.KEY1:
                self.logger.info("KEY1: Rover status check")
                self._log_rover_status()
            elif button == ButtonType.KEY2:
                self.adjust_brightness()
            elif button == ButtonType.KEY3:
                self.log_survey_point()
            elif button == ButtonType.JOY_PRESS:
                self.logger.info("JOY_PRESS: Emergency shutdown requested")
                self.running = False
    
    def _update_monitoring_data(self):
        """Update monitoring data from GPS and other sources"""
        try:
            # Update GPS satellite count and position
            if self.gps_controller:
                position = self.gps_controller.get_position()
                if position and hasattr(position, 'satellites_used'):
                    self.satellites_count = position.satellites_used
                    self.current_position = position
                else:
                    self.satellites_count = 0
                    self.current_position = None
                    
                # Update RTK status
                if self.gps_controller.has_rtk_fix():
                    self.rtk_status = "RTK Fixed"
                    self.point_logging_ready = True
                elif self.gps_controller.has_rtk_float():
                    self.rtk_status = "RTK Float"
                    self.point_logging_ready = True
                else:
                    self.rtk_status = "No RTK"
                    self.point_logging_ready = False
            
            # TODO: Update base connection status and signal strength from communication module
            # self.base_connected, self.signal_strength = communication_manager.get_base_status()
            
        except Exception as e:
            self.logger.error(f"Monitoring data update error: {e}")
    
    def _handle_rover_operations(self):
        """Handle ongoing rover operations"""
        try:
            # TODO: Maintain base station connection
            # TODO: Receive RTK corrections
            # TODO: Update position data
            pass
            
        except Exception as e:
            self.logger.error(f"Rover operations error: {e}")
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human readable format"""
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h{minutes}m"
        else:
            return f"{minutes}m"
    
    def _log_rover_status(self):
        """Log current rover status"""
        self.logger.info(f"Rover Status:")
        self.logger.info(f"  Satellites: {self.satellites_count}")
        self.logger.info(f"  RTK Status: {self.rtk_status}")
        self.logger.info(f"  Base Connected: {self.base_connected}")
        self.logger.info(f"  Signal Strength: {self.signal_strength}%")
        self.logger.info(f"  Points Logged: {self.points_logged}")
        self.logger.info(f"  Point Logging Ready: {self.point_logging_ready}")
        
        if self.current_position:
            self.logger.info(f"  Current Position: {self.current_position.latitude:.6f}, {self.current_position.longitude:.6f}")
            self.logger.info(f"  Accuracy: ±{self.current_position.accuracy_horizontal:.2f}m")
    
    def log_survey_point(self):
        """Log a survey point"""
        if not self.point_logging_ready:
            self.logger.warning("Point logging not ready - insufficient GPS accuracy")
            return
            
        if not self.current_position:
            self.logger.warning("No GPS position available for logging")
            return
            
        try:
            # TODO: Implement actual point logging to file/database
            self.points_logged += 1
            
            self.logger.info(f"Survey point {self.points_logged} logged:")
            self.logger.info(f"  Position: {self.current_position.latitude:.6f}, {self.current_position.longitude:.6f}")
            self.logger.info(f"  Elevation: {self.current_position.elevation:.2f}m")
            self.logger.info(f"  Accuracy: ±{self.current_position.accuracy_horizontal:.2f}m")
            self.logger.info(f"  RTK Status: {self.rtk_status}")
            self.logger.info(f"  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # TODO: Save to CSV file or database
            # self._save_point_to_file(self.current_position)
            
        except Exception as e:
            self.logger.error(f"Failed to log survey point: {e}")
    
    def adjust_brightness(self):
        """Adjust display brightness"""
        # Implementation similar to base station
        if self.oled and self.oled.device:
            # Cycle through brightness levels
            current_contrast = getattr(self.oled, 'brightness', 255)
            brightness_levels = [64, 128, 192, 255]
            current_index = brightness_levels.index(current_contrast) if current_contrast in brightness_levels else 0
            next_index = (current_index + 1) % len(brightness_levels)
            new_brightness = brightness_levels[next_index]
            
            self.oled.device.contrast(new_brightness)
            self.oled.brightness = new_brightness
            self.logger.info(f"Brightness adjusted to: {new_brightness}")
    
    def handle_navigation(self, direction: str):
        """Handle joystick navigation"""
        self.logger.info(f"Navigation: {direction}")
        # TODO: Handle menu navigation, position marking, etc.
    
    def shutdown(self):
        """Shutdown the rover gracefully"""
        if not self.running:
            return
            
        self.logger.info("Shutting down RTK Rover...")
        self.running = False
        
        # Stop button monitoring
        if self.button_api:
            self.button_api.stop()
            self.logger.info("Rover button API stopped")
        
        # Note: Hardware cleanup is handled by the calling bootloader
        self.logger.info("RTK Rover shutdown complete")


def main():
    """Standalone entry point for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RTK Rover')
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
            logging.FileHandler('/tmp/pi-rtk-rover.log')
        ]
    )
    
    # Create and run rover (without hardware for testing)
    try:
        rover = RTKRover()
        return rover.run()
    except Exception as e:
        logging.error(f"Rover startup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
