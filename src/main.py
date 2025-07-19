#!/usr/bin/env python3
"""
Pi RTK Surveyor Main Application
Integrated bootloader, base station, and rover functionality
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
from web.web_server import RTKWebServer


class PiRTKSurveyor:
    """Pi RTK Surveyor - integrated bootloader, base station, and rover functionality"""
    
    def __init__(self):
        """Initialize the bootloader"""
        self.running = False
        self.mode_selected = False
        self.selected_mode = None
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize GPIO manager first
        try:
            self.gpio_manager = get_gpio_manager()
        except RuntimeError as e:
            self.logger.error(f"GPIO initialization failed: {e}")
            raise
        
        # Hardware components for bootloader only
        self.oled: Optional[OLEDManager] = None
        self.button_api: Optional[ButtonAPI] = None
        self.system_monitor: Optional[SystemMonitor] = None
        self.gps_controller: Optional[LC29HController] = None
        
        # Application state
        self.display_mode = "splash"  # splash, menu, system_info, base_running, rover_running
        self.brightness_level = 255
        self.current_mode = None  # None, "base", "rover"
        self.mode_running = False
        
        # Base station state
        self.web_server: Optional[RTKWebServer] = None
        self.webserver_running = False
        self.wifi_hotspot_running = False
        self.rovers_connected = 0
        
        # Rover state  
        self.base_connected = False
        self.signal_strength = 0
        self.point_logging_ready = False
        
        # Common state
        self.points_logged = 0
        self.satellites_count = 0
        self.rtk_status = "Initializing"
        self.current_position = None
        
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
            
            # Initialize button API for bootloader
            self.button_api = ButtonAPI(app_context=self)
            self.logger.info("Button API initialized")
            
            # Initialize GPS controller with hardware detection
            self.gps_controller = self._initialize_gps_controller()
            if self.gps_controller:
                self.logger.info("GPS controller initialized successfully")
            else:
                self.logger.error("Failed to initialize GPS controller")
                return False
            
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
        """Run the Pi RTK Surveyor"""
        self.logger.info("Starting Pi RTK Surveyor...")
        
        # Initialize hardware
        if not self.initialize_hardware():
            self.logger.error("Failed to initialize hardware")
            return 1
        
        # Start hardware components
        if self.button_api:
            self.button_api.start()
        
        # Start GPS controller if available
        if self.gps_controller:
            if self.gps_controller.start():
                self.logger.info("GPS data acquisition started")
            else:
                self.logger.error("Failed to start GPS data acquisition")
                return 1
        
        # Show splash screen
        if self.oled:
            self.oled.show_splash_screen(duration=3.0)
            # Switch to menu mode after splash
            self.display_mode = "menu"
        
        # Main application loop
        self.running = True
        self.logger.info("Pi RTK Surveyor ready - waiting for mode selection")
        
        try:
            while self.running:
                try:
                    # Update display based on current mode
                    self._update_display()
                    
                    # Process button events
                    self._process_button_events()
                    
                    # Handle mode-specific operations
                    if self.mode_running:
                        if self.current_mode == "base":
                            self._handle_base_operations()
                        elif self.current_mode == "rover":
                            self._handle_rover_operations()
                    
                    # Small delay to prevent busy waiting
                    time.sleep(0.1 if not self.mode_running else 0.5)
                    
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                    time.sleep(1)  # Prevent rapid error loops
                    
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested by user")
        finally:
            self.cleanup()
            
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
            elif self.display_mode == "system_info":
                if self.system_monitor:
                    info = self.system_monitor.get_system_info()
                    self.oled.show_system_info(
                        cpu_temp=info['cpu_temp'],
                        memory_usage=info['memory_percent'],
                        battery_level=info['battery_level']
                    )
            elif self.display_mode == "base_running":
                self._update_base_display()
            elif self.display_mode == "rover_running":
                self._update_rover_display()
                        
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
                elif self.display_mode == "system_info":
                    self._handle_system_info_buttons(button, event_type)
                    
        except Exception as e:
            self.logger.error(f"Button processing error: {e}")
    
    def _handle_menu_buttons(self, button, event_type):
        """Handle button events in menu mode"""
        from hardware.button_manager import ButtonType, ButtonEvent
        
        if event_type == ButtonEvent.PRESS:
            if button == ButtonType.KEY1:
                # Show immediate feedback that base mode was selected
                if self.oled:
                    self.oled.show_base_init_screen("Starting", "BASE STATION Selected")
                time.sleep(1.0)
                
                self.current_mode = "base"
                self._start_base_station()
                self.logger.info("BASE STATION mode selected")
            elif button == ButtonType.KEY2:
                # Show immediate feedback that rover mode was selected
                if self.oled:
                    self.oled.show_rover_init_screen("Starting", "ROVER Selected")
                time.sleep(1.0)
                
                self.current_mode = "rover"
                self._start_rover()
                self.logger.info("ROVER mode selected")
            elif button == ButtonType.KEY3:
                self.display_mode = "system_info"
                self.logger.info("Switched to System Info mode")
    
    def _handle_system_info_buttons(self, button, event_type):
        """Handle button events in system info mode"""
        from hardware.button_manager import ButtonType, ButtonEvent
        
        if event_type == ButtonEvent.PRESS:
            if button in [ButtonType.KEY1, ButtonType.KEY2, ButtonType.KEY3]:
                if self.mode_running:
                    # Return to running mode display
                    if self.current_mode == "base":
                        self.display_mode = "base_running"
                    elif self.current_mode == "rover":
                        self.display_mode = "rover_running"
                else:
                    # Return to menu
                    self.display_mode = "menu"
                self.logger.info("Returned from system info")
    
    # =================================================================
    # BASE STATION FUNCTIONALITY
    # =================================================================
    
    def _start_base_station(self):
        """Start base station mode"""
        self.logger.info("Starting base station mode...")
        
        # Initialize base station components
        if not self._initialize_base_components():
            self.logger.error("Failed to initialize base station components")
            return
        
        # Run initialization sequence
        if not self._run_base_initialization():
            self.logger.error("Base station initialization failed")
            return
        
        # Switch to base station mode
        self.mode_running = True
        self.display_mode = "base_running"
        self.logger.info("Base station operational")
    
    def _initialize_base_components(self) -> bool:
        """Initialize base station specific components"""
        try:
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
    
    def _run_base_initialization(self) -> bool:
        """Run the base station initialization sequence"""
        try:
            # Step 1: Show base splash
            if self.oled:
                self.oled.show_base_init_screen("1/4", "Base Station Mode")
            time.sleep(1.5)
            
            # Step 2: Initialize controls
            if self.oled:
                self.oled.show_base_init_screen("2/4", "Initializing Controls...")
            time.sleep(1.0)
            
            # Step 3: Start web server
            if self.oled:
                self.oled.show_base_init_screen("3/4", "Starting Web Server...")
            
            if self.web_server:
                try:
                    self.web_server.start()
                    
                    # Wait for web server to start
                    timeout = 8.0
                    start_time = time.time()
                    
                    while time.time() - start_time < timeout:
                        if hasattr(self.web_server, 'startup_successful') and self.web_server.startup_successful:
                            self.webserver_running = True
                            break
                        time.sleep(0.5)
                        
                        if self.oled:
                            elapsed = int(time.time() - start_time)
                            self.oled.show_base_init_screen("3/4", f"Web Server... {elapsed}s")
                    
                    if self.webserver_running:
                        self.logger.info("Web server started successfully")
                    else:
                        self.logger.warning("Web server startup timeout")
                        
                except Exception as e:
                    self.logger.error(f"Web server startup error: {e}")
                    self.webserver_running = False
            
            # Step 4: Setup WiFi (placeholder)
            if self.oled:
                status = "Web: OK" if self.webserver_running else "Web: Failed"
                self.oled.show_base_init_screen("4/4", f"{status} | WiFi Setup...")
            time.sleep(1.5)
            
            self.wifi_hotspot_running = True  # Placeholder
            
            # Show final status
            if self.oled:
                web_status = "✓" if self.webserver_running else "✗"
                wifi_status = "✓" if self.wifi_hotspot_running else "✗"
                self.oled.show_base_init_screen("Done", f"Web:{web_status} WiFi:{wifi_status} Ready!")
            time.sleep(2.0)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Base initialization failed: {e}")
            return False
    
    def _update_base_display(self):
        """Update display for base station mode"""
        if not self.oled or not self.mode_running:
            return
        
        # Only update every few seconds to avoid flicker
        current_time = time.time()
        if hasattr(self, '_last_base_display_update'):
            if current_time - self._last_base_display_update < 2.0:
                return
        self._last_base_display_update = current_time
        
        try:
            # Get system info
            if self.system_monitor:
                info = self.system_monitor.get_system_info()
                battery_level = info.get('battery_level', 100.0)
                uptime = self._format_uptime(info.get('uptime', 0))
            else:
                battery_level = 100.0
                uptime = "0m"
            
            # Update monitoring data
            self._update_monitoring_data()
            
            # Show web server status in rovers field
            rovers_display = 1 if self.webserver_running else 0
            
            self.oled.show_base_monitoring(
                satellites=self.satellites_count,
                rovers_connected=rovers_display,
                battery_level=battery_level,
                uptime=uptime,
                points_logged=self.points_logged
            )
            
        except Exception as e:
            self.logger.error(f"Base display update error: {e}")
    
    def _handle_base_operations(self):
        """Handle ongoing base station operations"""
        try:
            # TODO: Handle rover connections
            # TODO: Broadcast RTK corrections
            # TODO: Log survey data
            pass
            
        except Exception as e:
            self.logger.error(f"Base operations error: {e}")
    
    def _handle_base_button_events(self, button, event_type):
        """Handle button events in base station mode"""
        from hardware.button_manager import ButtonType, ButtonEvent
        
        if event_type == ButtonEvent.PRESS:
            if button == ButtonType.KEY1:
                self.logger.info("KEY1: Base station status check")
                self._log_base_status()
            elif button == ButtonType.KEY2:
                self._adjust_brightness()
            elif button == ButtonType.KEY3:
                self.display_mode = "system_info"
                self.logger.info("Switched to system info")
            elif button == ButtonType.JOY_PRESS:
                self.logger.info("JOY_PRESS: Emergency shutdown requested")
                self.running = False
    
    def _log_base_status(self):
        """Log current base station status"""
        web_status = "Running" if self.webserver_running else "Stopped"
        
        self.logger.info(f"=== Base Station Status ===")
        self.logger.info(f"  Satellites: {self.satellites_count}")
        self.logger.info(f"  RTK Status: {self.rtk_status}")
        self.logger.info(f"  Rovers Connected: {self.rovers_connected}")
        self.logger.info(f"  Points Logged: {self.points_logged}")
        self.logger.info(f"  Web Server: {web_status}")
        self.logger.info(f"  WiFi Hotspot: {'Running' if self.wifi_hotspot_running else 'Stopped'}")
        self.logger.info(f"==========================")
    
    # =================================================================
    # ROVER FUNCTIONALITY
    # =================================================================
    
    def _start_rover(self):
        """Start rover mode"""
        self.logger.info("Starting rover mode...")
        
        # Run initialization sequence
        if not self._run_rover_initialization():
            self.logger.error("Rover initialization failed")
            return
        
        # Switch to rover mode
        self.mode_running = True
        self.display_mode = "rover_running"
        self.logger.info("Rover operational")
    
    def _run_rover_initialization(self) -> bool:
        """Run the rover initialization sequence"""
        try:
            # Step 1: Show rover splash
            if self.oled:
                self.oled.show_rover_init_screen("1/2", "Rover Mode")
            time.sleep(2)
            
            # Step 2: Connect to base station
            if self.oled:
                self.oled.show_rover_init_screen("2/2", "Searching for base...")
            time.sleep(2)
            
            # Simulate base connection
            if self.oled:
                self.oled.show_rover_init_screen("2/2", "Base found! Connecting...")
            time.sleep(2)
            
            # TODO: Implement actual base station connection
            self.base_connected = True
            self.signal_strength = 85
            self.point_logging_ready = True
            
            return True
            
        except Exception as e:
            self.logger.error(f"Rover initialization failed: {e}")
            return False
    
    def _update_rover_display(self):
        """Update display for rover mode"""
        if not self.oled or not self.mode_running:
            return
            
        try:
            # Get system info
            if self.system_monitor:
                info = self.system_monitor.get_system_info()
                battery_level = info['battery_level']
                uptime = self._format_uptime(info['uptime'])
            else:
                battery_level = 0.0
                uptime = "0m"
            
            # Update monitoring data
            self._update_monitoring_data()
            
            self.oled.show_rover_monitoring(
                satellites=self.satellites_count,
                base_connected=self.base_connected,
                signal_strength=self.signal_strength,
                battery_level=battery_level,
                uptime=uptime,
                point_ready=self.point_logging_ready
            )
                        
        except Exception as e:
            self.logger.error(f"Rover display update error: {e}")
    
    def _handle_rover_operations(self):
        """Handle ongoing rover operations"""
        try:
            # TODO: Maintain base station connection
            # TODO: Receive RTK corrections
            # TODO: Update position data
            pass
            
        except Exception as e:
            self.logger.error(f"Rover operations error: {e}")
    
    def _handle_rover_button_events(self, button, event_type):
        """Handle button events in rover mode"""
        from hardware.button_manager import ButtonType, ButtonEvent
        
        if event_type == ButtonEvent.PRESS:
            if button == ButtonType.KEY1:
                self.logger.info("KEY1: Rover status check")
                self._log_rover_status()
            elif button == ButtonType.KEY2:
                self._adjust_brightness()
            elif button == ButtonType.KEY3:
                self._log_survey_point()
            elif button == ButtonType.JOY_PRESS:
                self.logger.info("JOY_PRESS: Emergency shutdown requested")
                self.running = False
    
    def _log_rover_status(self):
        """Log current rover status"""
        self.logger.info(f"=== Rover Status ===")
        self.logger.info(f"  Satellites: {self.satellites_count}")
        self.logger.info(f"  RTK Status: {self.rtk_status}")
        self.logger.info(f"  Base Connected: {self.base_connected}")
        self.logger.info(f"  Signal Strength: {self.signal_strength}%")
        self.logger.info(f"  Points Logged: {self.points_logged}")
        self.logger.info(f"  Point Logging Ready: {self.point_logging_ready}")
        
        if self.current_position:
            self.logger.info(f"  Position: {self.current_position.latitude:.6f}, {self.current_position.longitude:.6f}")
    
    def _log_survey_point(self):
        """Log a survey point (production hardware only)"""
        # Check if GPS hardware is available
        if not self.gps_controller or not self.gps_controller.connected:
            self.logger.error("Cannot log point - GPS hardware not available")
            if self.oled:
                self.oled.show_rover_init_screen("Error", "GPS Hardware Required")
                time.sleep(2.0)
            return
        
        # Check if GPS has sufficient accuracy for surveying
        if not self.point_logging_ready:
            self.logger.warning("Point logging not ready - insufficient GPS accuracy")
            self.logger.warning(f"Current RTK status: {self.rtk_status}")
            if self.oled:
                self.oled.show_rover_init_screen("Wait", f"Need RTK Fix: {self.rtk_status}")
                time.sleep(2.0)
            return
        
        # Check if we have a valid position
        if not self.current_position or not self.current_position.valid:
            self.logger.warning("No valid GPS position available for logging")
            return
        
        try:
            self.points_logged += 1
            
            # Log detailed point information
            self.logger.info(f"=== Survey Point {self.points_logged} ===")
            self.logger.info(f"  Latitude:  {self.current_position.latitude:.8f}")
            self.logger.info(f"  Longitude: {self.current_position.longitude:.8f}")
            self.logger.info(f"  Elevation: {self.current_position.elevation:.3f}m")
            self.logger.info(f"  RTK Status: {self.rtk_status}")
            self.logger.info(f"  Fix Type: {self.current_position.fix_type.name}")
            self.logger.info(f"  Satellites: {self.current_position.satellites_used}")
            self.logger.info(f"  HDOP: {self.current_position.hdop:.2f}")
            self.logger.info(f"  Horizontal Accuracy: {self.current_position.accuracy_horizontal:.3f}m")
            self.logger.info(f"  Vertical Accuracy: {self.current_position.accuracy_vertical:.3f}m")
            self.logger.info(f"  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info("================================")
            
            # Show success feedback on display
            if self.oled:
                self.oled.show_rover_init_screen("Success", f"Point {self.points_logged} Logged!")
                time.sleep(1.5)
            
            # TODO: Save to CSV file in data/surveys/ directory
            # This will be implemented in Task 2: Point Logging System
            
        except Exception as e:
            self.logger.error(f"Failed to log survey point: {e}")
            if self.oled:
                self.oled.show_rover_init_screen("Error", "Point Log Failed")
                time.sleep(2.0)
    
    # =================================================================
    # COMMON FUNCTIONALITY
    # =================================================================
    
    def _update_monitoring_data(self):
        """Update monitoring data from GPS and other sources"""
        try:
            # Update GPS satellite count and RTK status
            if self.gps_controller and self.gps_controller.connected:
                # Get current position from GPS
                position = self.gps_controller.get_position()
                
                if position and position.valid:
                    self.satellites_count = position.satellites_used
                    self.current_position = position
                    
                    # Update RTK status based on fix type
                    if self.gps_controller.has_rtk_fix():
                        self.rtk_status = "RTK Fixed"
                        if self.current_mode == "rover":
                            self.point_logging_ready = True
                    elif self.gps_controller.has_rtk_float():
                        self.rtk_status = "RTK Float"
                        if self.current_mode == "rover":
                            self.point_logging_ready = True
                    elif position.fix_type.value > 0:
                        self.rtk_status = f"GPS {position.fix_type.name}"
                        if self.current_mode == "rover":
                            self.point_logging_ready = False
                    else:
                        self.rtk_status = "No Fix"
                        if self.current_mode == "rover":
                            self.point_logging_ready = False
                else:
                    # GPS connected but no valid position yet
                    self.satellites_count = 0
                    self.rtk_status = "Acquiring Signal"
                    if self.current_mode == "rover":
                        self.point_logging_ready = False
                        
                # Get GPS statistics for connection monitoring
                stats = self.gps_controller.get_statistics()
                if stats.get('time_since_last_message', 999) > 10:
                    self.rtk_status = "GPS Timeout"
                    
            else:
                # GPS not available or not connected
                self.satellites_count = 0
                self.rtk_status = "GPS Hardware Not Available"
                if self.current_mode == "rover":
                    self.point_logging_ready = False
            
        except Exception as e:
            self.logger.error(f"Monitoring data update error: {e}")
            self.satellites_count = 0
            self.rtk_status = "GPS Error"
            if self.current_mode == "rover":
                self.point_logging_ready = False
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human readable format"""
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h{minutes}m"
        else:
            return f"{minutes}m"
    
    def _adjust_brightness(self):
        """Adjust display brightness"""
        if self.oled and self.oled.device:
            brightness_levels = [64, 128, 192, 255]
            current_index = brightness_levels.index(self.brightness_level) if self.brightness_level in brightness_levels else 0
            next_index = (current_index + 1) % len(brightness_levels)
            self.brightness_level = brightness_levels[next_index]
            
            self.oled.device.contrast(self.brightness_level)
            self.logger.info(f"Brightness adjusted to: {self.brightness_level}")
    
    def _initialize_gps_controller(self) -> Optional[LC29HController]:
        """Initialize GPS controller with hardware detection (production mode only)"""
        try:
            # Attempt to initialize with LC29H hardware on UART
            self.logger.info("Initializing LC29H GNSS controller for production hardware...")
            
            # Try common UART ports and baud rates for LC29H RTK HAT
            uart_ports = ['/dev/ttyAMA0', '/dev/serial0', '/dev/ttyS0']
            baud_rates = [38400, 9600, 115200, 57600, 19200]
            
            for port in uart_ports:
                for baud in baud_rates:
                    try:
                        self.logger.info(f"Attempting GPS connection on {port} at {baud} baud")
                        gps = LC29HController(port=port, baudrate=baud, simulate=False)
                        
                        # Test connection
                        if gps.connect():
                            self.logger.info(f"Successfully connected to LC29H on {port} at {baud} baud")
                            return gps
                        else:
                            self.logger.debug(f"No response on {port} at {baud} baud")
                            
                    except Exception as e:
                        self.logger.debug(f"GPS connection error on {port} at {baud}: {e}")
                        continue
            
            # If we get here, no GPS hardware was detected
            self.logger.error("No LC29H GNSS hardware detected on any UART port")
            self.logger.error("Please ensure:")
            self.logger.error("  1. LC29H RTK HAT is properly connected")
            self.logger.error("  2. UART is enabled in raspi-config")
            self.logger.error("  3. Serial console is disabled")
            return None
            
        except Exception as e:
            self.logger.error(f"GPS controller initialization failed: {e}")
            return None
    
    def cleanup(self):
        """Full cleanup of all resources"""
        if not self.running:
            return
            
        self.logger.info("Shutting down Pi RTK Surveyor...")
        self.running = False
        
        # Stop web server if running
        if self.web_server:
            self.web_server.stop()
            self.logger.info("Web server stopped")
        
        # Clean up components in reverse order of initialization
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
    
    # Update button event processing to handle mode-specific events
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
                elif self.display_mode == "system_info":
                    self._handle_system_info_buttons(button, event_type)
                elif self.display_mode == "base_running":
                    self._handle_base_button_events(button, event_type)
                elif self.display_mode == "rover_running":
                    self._handle_rover_button_events(button, event_type)
                    
        except Exception as e:
            self.logger.error(f"Button processing error: {e}")
    
    # Methods for button API compatibility
    def adjust_brightness(self):
        """Adjust display brightness (compatibility method)"""
        self._adjust_brightness()
    
    def handle_navigation(self, direction: str):
        """Handle joystick navigation"""
        self.logger.info(f"Navigation: {direction}")


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
    
    # Create and run surveyor
    try:
        surveyor = PiRTKSurveyor()
        return surveyor.run()
    except Exception as e:
        logging.error(f"Pi RTK Surveyor startup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
