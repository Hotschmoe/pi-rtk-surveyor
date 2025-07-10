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

# Add software directory to Python path
software_dir = Path(__file__).parent
sys.path.insert(0, str(software_dir))

# Import local modules
from display.oled_manager import OLEDManager
from monitoring.system_monitor import SystemMonitor

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
        
        # Initialize components
        self.oled = None
        self.system_monitor = None
        
        # Set up logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _setup_logging(self):
        """Configure application logging"""
        log_dir = Path(__file__).parent.parent / "data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / "rtk_surveyor.log"
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        
        # Set up file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(file_formatter)
        
        # Set up console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.shutdown()
        
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
            # Show device selection screen
            if self.oled:
                self.oled.show_device_selection()
                self.logger.info("Waiting for device role selection...")
            
            # For now, just cycle through different displays every 5 seconds
            # This will be replaced with actual button handling and GPS integration
            display_mode = 0
            last_update = time.time()
            
            while self.running:
                current_time = time.time()
                
                # Update display every 5 seconds for demo
                if current_time - last_update >= 5.0:
                    if self.system_monitor and self.oled:
                        sys_info = self.system_monitor.get_system_info()
                        
                        if display_mode == 0:
                            self.oled.show_system_info(
                                cpu_temp=sys_info.get('cpu_temp', 0),
                                memory_usage=sys_info.get('memory_percent', 0),
                                battery_level=sys_info.get('battery_level', 100)
                            )
                            display_mode = 1
                        elif display_mode == 1:
                            self.oled.show_gps_status(
                                fix_type="Acquiring...",
                                lat=0, lon=0, accuracy=0
                            )
                            display_mode = 2
                        else:
                            self.oled.show_device_selection()
                            display_mode = 0
                            
                    last_update = current_time
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
            
    def shutdown(self):
        """Shutdown the application gracefully"""
        if not self.running:
            return
            
        self.logger.info("Shutting down Pi RTK Surveyor...")
        self.running = False
        
        # Clean up components
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
    
    args = parser.parse_args()
    
    # Adjust logging level if debug mode
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and start application
    app = RTKSurveyorApp(simulate_hardware=args.simulate)
    
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
