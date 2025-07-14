#!/usr/bin/env python3
"""
Pi RTK Surveyor Main Application - Bootloader & Mode Selection
Handles hardware initialization and device role selection only
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


class PiRTKBootloader:
    """Bootloader for Pi RTK Surveyor - handles hardware init and mode selection"""
    
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
        self.display_mode = "splash"  # splash, menu, system_info
        self.brightness_level = 255
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.logger.info("Pi RTK Surveyor Bootloader initialized")
    
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
            
            # Initialize GPS controller (basic init only)
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
        """Run the bootloader"""
        self.logger.info("Starting Pi RTK Surveyor Bootloader...")
        
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
        
        # Main bootloader loop - wait for mode selection
        self.running = True
        self.logger.info("Pi RTK Surveyor Bootloader ready - waiting for mode selection")
        
        try:
            while self.running and not self.mode_selected:
                try:
                    # Update display based on current mode
                    self._update_display()
                    
                    # Process button events
                    self._process_button_events()
                    
                    # Small delay to prevent busy waiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.logger.error(f"Error in bootloader loop: {e}")
                    time.sleep(1)  # Prevent rapid error loops
                    
            # Mode has been selected - hand off to appropriate module
            if self.mode_selected:
                return self._launch_selected_mode()
                
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested by user")
        finally:
            self.cleanup_bootloader()
            
        return 0
    
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        self.logger.info(f"Received signal {signum}, shutting down bootloader...")
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
                self.selected_mode = "base"
                self.mode_selected = True
                self.logger.info("BASE STATION mode selected")
            elif button == ButtonType.KEY2:
                self.selected_mode = "rover"
                self.mode_selected = True
                self.logger.info("ROVER mode selected")
            elif button == ButtonType.KEY3:
                self.display_mode = "system_info"
                self.logger.info("Switched to System Info mode")
    
    def _handle_system_info_buttons(self, button, event_type):
        """Handle button events in system info mode"""
        from hardware.button_manager import ButtonType, ButtonEvent
        
        if event_type == ButtonEvent.PRESS:
            if button in [ButtonType.KEY1, ButtonType.KEY2, ButtonType.KEY3]:
                self.display_mode = "menu"
                self.logger.info("Returned to menu")
    
    def _launch_selected_mode(self) -> int:
        """Launch the selected mode (base or rover)"""
        self.logger.info(f"Launching {self.selected_mode} mode...")
        
        # Clean up bootloader resources but keep hardware initialized
        self._cleanup_bootloader_only()
        
        try:
            if self.selected_mode == "base":
                return self._launch_base_station()
            elif self.selected_mode == "rover":
                return self._launch_rover()
            else:
                self.logger.error(f"Unknown mode: {self.selected_mode}")
                return 1
                
        except Exception as e:
            self.logger.error(f"Failed to launch {self.selected_mode} mode: {e}")
            return 1
    
    def _launch_base_station(self) -> int:
        """Launch base station mode"""
        try:
            from rtk_base.rtk_base import RTKBaseStation
            
            # Pass initialized hardware to base station
            base_station = RTKBaseStation(
                oled_manager=self.oled,
                system_monitor=self.system_monitor,
                gps_controller=self.gps_controller,
                gpio_manager=self.gpio_manager
            )
            
            return base_station.run()
            
        except ImportError as e:
            self.logger.error(f"Failed to import RTKBaseStation: {e}")
            return 1
    
    def _launch_rover(self) -> int:
        """Launch rover mode"""
        try:
            from rtk_rover.rtk_rover import RTKRover
            
            # Pass initialized hardware to rover
            rover = RTKRover(
                oled_manager=self.oled,
                system_monitor=self.system_monitor,
                gps_controller=self.gps_controller,
                gpio_manager=self.gpio_manager
            )
            
            return rover.run()
            
        except ImportError as e:
            self.logger.error(f"Failed to import RTKRover: {e}")
            return 1
    
    def _cleanup_bootloader_only(self):
        """Clean up bootloader-specific resources only"""
        # Stop button monitoring for bootloader
        if self.button_api:
            self.button_api.stop()
            self.logger.info("Bootloader button API stopped")
        
        # Don't cleanup hardware - pass it to the selected mode
        self.logger.info("Bootloader cleanup complete - hardware passed to selected mode")
    
    def cleanup_bootloader(self):
        """Full cleanup of all bootloader resources"""
        if not self.running:
            return
            
        self.logger.info("Shutting down Pi RTK Surveyor Bootloader...")
        self.running = False
        
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
        
        self.logger.info("Bootloader shutdown complete")
    
    # Methods for button API compatibility
    def adjust_brightness(self):
        """Adjust display brightness"""
        brightness_levels = [64, 128, 192, 255]
        current_index = brightness_levels.index(self.brightness_level) if self.brightness_level in brightness_levels else 0
        next_index = (current_index + 1) % len(brightness_levels)
        self.brightness_level = brightness_levels[next_index]
        
        if self.oled and self.oled.device:
            self.oled.device.contrast(self.brightness_level)
            
        self.logger.info(f"Brightness adjusted to: {self.brightness_level}")
    
    def handle_navigation(self, direction: str):
        """Handle joystick navigation"""
        self.logger.info(f"Navigation: {direction}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pi RTK Surveyor Bootloader')
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
    
    # Create and run bootloader
    try:
        bootloader = PiRTKBootloader()
        return bootloader.run()
    except Exception as e:
        logging.error(f"Bootloader startup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
