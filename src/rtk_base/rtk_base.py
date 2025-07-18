#!/usr/bin/env python3
"""
RTK Base Station Implementation
Handles all base station operations including web server and monitoring
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
from web.web_server import RTKWebServer


class RTKBaseStation:
    """RTK Base Station - handles all base station operations"""
    
    def __init__(self, oled_manager: Optional[OLEDManager] = None,
                 system_monitor: Optional[SystemMonitor] = None,
                 gps_controller: Optional[LC29HController] = None,
                 gpio_manager: Optional[GPIOManager] = None):
        """
        Initialize RTK Base Station
        
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
        
        # Base station specific components
        self.button_api: Optional[ButtonAPI] = None
        self.web_server: Optional[RTKWebServer] = None
        
        # Base station state
        self.rovers_connected = 0
        self.points_logged = 0
        self.webserver_running = False
        self.wifi_hotspot_running = False
        
        # Monitoring data
        self.satellites_count = 0
        self.rtk_status = "Initializing"
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.logger.info("RTK Base Station initialized")
    
    def run(self) -> int:
        """Run the base station"""
        self.logger.info("Starting RTK Base Station...")
        
        # Initialize base station specific components
        if not self._initialize_base_components():
            self.logger.error("Failed to initialize base station components")
            return 1
        
        # Start initialization sequence
        if not self._run_initialization_sequence():
            self.logger.error("Base station initialization failed")
            return 1
        
        # Main base station loop
        self.running = True
        self.initialization_complete = True
        self.logger.info("RTK Base Station operational")
        
        try:
            while self.running:
                try:
                    # Update display
                    self._update_display()
                    
                    # Process button events
                    self._process_button_events()
                    
                    # Update monitoring data
                    self._update_monitoring_data()
                    
                    # Handle base station operations
                    self._handle_base_operations()
                    
                    # Small delay to prevent busy waiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.logger.error(f"Error in base station loop: {e}")
                    time.sleep(1)  # Prevent rapid error loops
                    
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested by user")
        finally:
            self.shutdown()
            
        return 0
    
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        self.logger.info(f"Received signal {signum}, shutting down base station...")
        self.running = False
    
    def _initialize_base_components(self) -> bool:
        """Initialize base station specific components"""
        try:
            # Initialize button API for base station operations
            self.button_api = ButtonAPI(app_context=self)
            self.button_api.start()
            self.logger.info("Base station button API initialized")
            
            # Initialize web server
            self.web_server = RTKWebServer(
                gps_controller=self.gps_controller,
                system_monitor=self.system_monitor,
                host='0.0.0.0',
                port=5000
            )
            self.logger.info("Web server initialized")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize base components: {e}")
            return False
    
    def _run_initialization_sequence(self) -> bool:
        """Run the base station initialization sequence with display updates"""
        try:
            # Step 1: Show base splash
            self.logger.info("Base station initialization sequence started")
            if self.oled:
                self.oled.show_base_init_screen("1/3", "Base Station Mode")
            time.sleep(2)
            
            # Step 2: Initialize web server
            if self.oled:
                self.oled.show_base_init_screen("2/3", "Starting Web Server...")
            
            # Start web server in background thread with error handling
            self.logger.info("Starting web server...")
            try:
                web_thread = threading.Thread(target=self._start_web_server, daemon=True)
                web_thread.start()
                
                # Give web server time to start, but don't wait forever
                start_time = time.time()
                timeout = 10  # 10 second timeout
                
                while time.time() - start_time < timeout:
                    if self.webserver_running or not web_thread.is_alive():
                        break
                    time.sleep(0.5)
                
                if self.webserver_running:
                    self.logger.info("Web server started successfully")
                else:
                    self.logger.warning("Web server may not have started properly, continuing...")
                    
            except Exception as e:
                self.logger.error(f"Web server startup error: {e}")
                self.webserver_running = False
            
            # Step 3: Initialize WiFi hotspot (placeholder)
            if self.oled:
                self.oled.show_base_init_screen("3/3", "Starting WiFi Hotspot...")
            time.sleep(2)
            
            # TODO: Implement actual WiFi hotspot
            self.wifi_hotspot_running = True
            self.logger.info("WiFi hotspot started (placeholder)")
            
            self.logger.info("Base station initialization sequence complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization sequence failed: {e}")
            return False
    
    def _start_web_server(self):
        """Start the web server in background thread"""
        try:
            if self.web_server:
                self.logger.info("Web server thread starting...")
                self.webserver_running = True  # Set flag before starting
                self.web_server.start()
            else:
                self.logger.error("Web server not initialized")
                self.webserver_running = False
        except Exception as e:
            self.logger.error(f"Web server failed to start: {e}")
            self.webserver_running = False
    
    def _update_display(self):
        """Update the OLED display with base station monitoring info"""
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
            
            self.oled.show_base_monitoring(
                satellites=self.satellites_count,
                rovers_connected=self.rovers_connected,
                battery_level=battery_level,
                uptime=uptime,
                points_logged=self.points_logged
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
                self._handle_base_button_events(button, event_type)
                    
        except Exception as e:
            self.logger.error(f"Button processing error: {e}")
    
    def _handle_base_button_events(self, button, event_type):
        """Handle button events in base station mode"""
        from hardware.button_manager import ButtonType, ButtonEvent
        
        if event_type == ButtonEvent.PRESS:
            if button == ButtonType.KEY1:
                self.logger.info("KEY1: Base station status check")
                self._log_base_status()
            elif button == ButtonType.KEY2:
                self.adjust_brightness()
            elif button == ButtonType.KEY3:
                self.toggle_logging()
            elif button == ButtonType.JOY_PRESS:
                self.logger.info("JOY_PRESS: Emergency shutdown requested")
                self.running = False
    
    def _update_monitoring_data(self):
        """Update monitoring data from GPS and other sources"""
        try:
            # Update GPS satellite count
            if self.gps_controller:
                position = self.gps_controller.get_position()
                if position and hasattr(position, 'satellites_used'):
                    self.satellites_count = position.satellites_used
                else:
                    self.satellites_count = 0
                    
                # Update RTK status
                if self.gps_controller.has_rtk_fix():
                    self.rtk_status = "RTK Fixed"
                elif self.gps_controller.has_rtk_float():
                    self.rtk_status = "RTK Float"
                else:
                    self.rtk_status = "No RTK"
            
            # TODO: Update rover connection count from communication module
            # self.rovers_connected = communication_manager.get_rover_count()
            
        except Exception as e:
            self.logger.error(f"Monitoring data update error: {e}")
    
    def _handle_base_operations(self):
        """Handle ongoing base station operations"""
        try:
            # TODO: Handle rover connections
            # TODO: Broadcast RTK corrections
            # TODO: Log survey data
            pass
            
        except Exception as e:
            self.logger.error(f"Base operations error: {e}")
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human readable format"""
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h{minutes}m"
        else:
            return f"{minutes}m"
    
    def _log_base_status(self):
        """Log current base station status"""
        self.logger.info(f"Base Station Status:")
        self.logger.info(f"  Satellites: {self.satellites_count}")
        self.logger.info(f"  RTK Status: {self.rtk_status}")
        self.logger.info(f"  Rovers Connected: {self.rovers_connected}")
        self.logger.info(f"  Points Logged: {self.points_logged}")
        self.logger.info(f"  Web Server: {'Running' if self.webserver_running else 'Stopped'}")
        self.logger.info(f"  WiFi Hotspot: {'Running' if self.wifi_hotspot_running else 'Stopped'}")
    
    def adjust_brightness(self):
        """Adjust display brightness"""
        # Implementation similar to bootloader
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
    
    def toggle_logging(self):
        """Toggle survey data logging"""
        # TODO: Implement actual survey data logging
        self.logger.info("Survey logging toggled (placeholder)")
    
    def handle_navigation(self, direction: str):
        """Handle joystick navigation"""
        self.logger.info(f"Navigation: {direction}")
        # TODO: Handle menu navigation, settings, etc.
    
    def shutdown(self):
        """Shutdown the base station gracefully"""
        if not self.running:
            return
            
        self.logger.info("Shutting down RTK Base Station...")
        self.running = False
        
        # Stop web server
        if self.web_server:
            self.web_server.stop()
            self.logger.info("Web server stopped")
        
        # Stop button monitoring
        if self.button_api:
            self.button_api.stop()
            self.logger.info("Base station button API stopped")
        
        # Note: Hardware cleanup is handled by the calling bootloader
        self.logger.info("RTK Base Station shutdown complete")


def main():
    """Standalone entry point for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RTK Base Station')
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
            logging.FileHandler('/tmp/pi-rtk-base.log')
        ]
    )
    
    # Create and run base station (without hardware for testing)
    try:
        base_station = RTKBaseStation()
        return base_station.run()
    except Exception as e:
        logging.error(f"Base station startup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
