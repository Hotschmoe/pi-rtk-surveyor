#!/usr/bin/env python3
"""
OLED Display Manager for Pi RTK Surveyor
Handles Waveshare 1.3" OLED HAT display functionality
"""

import time
import threading
from typing import Optional, Callable
from PIL import Image, ImageDraw, ImageFont
import logging

try:
    from luma.core.interface.serial import spi
    from luma.core.render import canvas
    from luma.oled.device import sh1106
    DISPLAY_AVAILABLE = True
except ImportError:
    DISPLAY_AVAILABLE = False
    logging.warning("OLED display libraries not available - running in simulation mode")

class OLEDManager:
    """Manages OLED display operations for Pi RTK Surveyor"""
    
    def __init__(self, simulate_display: bool = False):
        """
        Initialize OLED display manager
        
        Args:
            simulate_display: If True, runs without hardware (for development)
        """
        self.simulate_display = simulate_display or not DISPLAY_AVAILABLE
        self.device = None
        self.display_thread = None
        self.running = False
        self.current_screen = None
        self.brightness = 255  # 0-255
        
        # Display dimensions (Waveshare 1.3" OLED)
        self.width = 128
        self.height = 64
        
        # Initialize display
        self._init_display()
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
    def _init_display(self):
        """Initialize the physical OLED display"""
        if self.simulate_display:
            self.logger.info("Running OLED in simulation mode")
            return
            
        try:
            # Waveshare 1.3" OLED uses SH1106 controller
            serial = spi(device=0, port=0)
            self.device = sh1106(serial, width=self.width, height=self.height)
            self.device.contrast(self.brightness)
            self.logger.info("OLED display initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize OLED display: {e}")
            self.simulate_display = True
            
    def show_splash_screen(self, duration: float = 3.0):
        """
        Display startup splash screen
        
        Args:
            duration: How long to show splash screen (seconds)
        """
        def draw_splash(draw, width, height):
            # Clear screen
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            
            # Title
            try:
                font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Pi RTK Surveyor title
            title = "Pi RTK Surveyor"
            title_bbox = draw.textbbox((0, 0), title, font=font_large)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text(((width - title_width) // 2, 8), title, font=font_large, fill=255)
            
            # Version and status
            version = "v1.0.0"
            status = "Initializing..."
            
            version_bbox = draw.textbbox((0, 0), version, font=font_small)
            version_width = version_bbox[2] - version_bbox[0]
            draw.text(((width - version_width) // 2, 28), version, font=font_small, fill=255)
            
            status_bbox = draw.textbbox((0, 0), status, font=font_small)
            status_width = status_bbox[2] - status_bbox[0]
            draw.text(((width - status_width) // 2, 42), status, font=font_small, fill=255)
            
            # Progress bar
            bar_width = 80
            bar_height = 4
            bar_x = (width - bar_width) // 2
            bar_y = 55
            
            # Draw progress bar outline
            draw.rectangle((bar_x, bar_y, bar_x + bar_width, bar_y + bar_height), outline=255, fill=0)
            
            # Animate progress bar
            progress = int((time.time() % 2) * (bar_width / 2))
            if progress > 0:
                draw.rectangle((bar_x + 1, bar_y + 1, bar_x + progress, bar_y + bar_height - 1), fill=255)
        
        self._display_content(draw_splash, duration)
        
    def show_device_selection(self):
        """Display device role selection screen"""
        def draw_selection(draw, width, height):
            # Clear screen
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            
            try:
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
                font_option = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                font_title = ImageFont.load_default()
                font_option = ImageFont.load_default()
            
            # Title
            title = "Select Mode:"
            title_bbox = draw.textbbox((0, 0), title, font=font_title)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text(((width - title_width) // 2, 5), title, font=font_title, fill=255)
            
            # Options
            option1 = "1) Base Station"
            option2 = "2) Rover"
            
            draw.text((10, 25), option1, font=font_option, fill=255)
            draw.text((10, 40), option2, font=font_option, fill=255)
            
            # Instructions
            instruction = "Press KEY1/2 to select"
            instr_bbox = draw.textbbox((0, 0), instruction, font=font_option)
            instr_width = instr_bbox[2] - instr_bbox[0]
            draw.text(((width - instr_width) // 2, 55), instruction, font=font_option, fill=255)
        
        self._display_content(draw_selection)
        
    def show_system_info(self, cpu_temp: float = 0, memory_usage: float = 0, 
                        battery_level: float = 100):
        """
        Display system information screen
        
        Args:
            cpu_temp: CPU temperature in Celsius
            memory_usage: Memory usage percentage
            battery_level: Battery level percentage
        """
        def draw_system_info(draw, width, height):
            # Clear screen
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            
            try:
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
            except:
                font_small = ImageFont.load_default()
            
            # System info
            draw.text((5, 5), "System Status", font=font_small, fill=255)
            draw.text((5, 18), f"CPU: {cpu_temp:.1f}°C", font=font_small, fill=255)
            draw.text((5, 30), f"Mem: {memory_usage:.1f}%", font=font_small, fill=255)
            draw.text((5, 42), f"Bat: {battery_level:.1f}%", font=font_small, fill=255)
            
            # Battery indicator
            bat_x, bat_y = 80, 42
            bat_width, bat_height = 30, 8
            
            # Battery outline
            draw.rectangle((bat_x, bat_y, bat_x + bat_width, bat_y + bat_height), outline=255, fill=0)
            draw.rectangle((bat_x + bat_width, bat_y + 2, bat_x + bat_width + 2, bat_y + bat_height - 2), fill=255)
            
            # Battery fill
            fill_width = int((battery_level / 100) * (bat_width - 2))
            if fill_width > 0:
                draw.rectangle((bat_x + 1, bat_y + 1, bat_x + 1 + fill_width, bat_y + bat_height - 1), fill=255)
        
        self._display_content(draw_system_info)
        
    def show_gps_status(self, fix_type: str = "No Fix", lat: float = 0, 
                       lon: float = 0, accuracy: float = 0):
        """
        Display GPS status information
        
        Args:
            fix_type: GPS fix type (No Fix, 2D, 3D, RTK Float, RTK Fixed)
            lat: Latitude
            lon: Longitude  
            accuracy: Position accuracy in meters
        """
        def draw_gps_status(draw, width, height):
            # Clear screen
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            
            try:
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
            except:
                font_small = ImageFont.load_default()
            
            # GPS Status
            draw.text((5, 5), "GPS Status", font=font_small, fill=255)
            draw.text((5, 17), f"Fix: {fix_type}", font=font_small, fill=255)
            
            if lat != 0 or lon != 0:
                draw.text((5, 29), f"Lat: {lat:.6f}", font=font_small, fill=255)
                draw.text((5, 41), f"Lon: {lon:.6f}", font=font_small, fill=255)
                draw.text((5, 53), f"Acc: ±{accuracy:.2f}m", font=font_small, fill=255)
            else:
                draw.text((5, 35), "Waiting for GPS...", font=font_small, fill=255)
        
        self._display_content(draw_gps_status)
        
    def clear_display(self):
        """Clear the display"""
        if self.simulate_display:
            print("OLED: Display cleared")
            return
            
        if self.device:
            self.device.clear()
            
    def set_brightness(self, brightness: int):
        """
        Set display brightness
        
        Args:
            brightness: Brightness level 0-255
        """
        self.brightness = max(0, min(255, brightness))
        
        if not self.simulate_display and self.device:
            self.device.contrast(self.brightness)
            
        self.logger.info(f"Display brightness set to {self.brightness}")
        
    def _display_content(self, draw_function: Callable, duration: Optional[float] = None):
        """
        Display content using provided drawing function
        
        Args:
            draw_function: Function that takes (draw, width, height) parameters
            duration: Optional duration to show content
        """
        if self.simulate_display:
            print(f"OLED: Displaying content for {duration or 'indefinite'} seconds")
            if duration:
                time.sleep(duration)
            return
            
        if not self.device:
            return
            
        with canvas(self.device) as draw:
            draw_function(draw, self.width, self.height)
            
        if duration:
            time.sleep(duration)
            
    def start_display_loop(self):
        """Start the display update loop in a separate thread"""
        if self.running:
            return
            
        self.running = True
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
        self.logger.info("Display loop started")
        
    def stop_display_loop(self):
        """Stop the display update loop"""
        self.running = False
        if self.display_thread:
            self.display_thread.join(timeout=1.0)
        self.logger.info("Display loop stopped")
        
    def _display_loop(self):
        """Main display update loop"""
        while self.running:
            # Update current screen if needed
            time.sleep(0.1)  # 10 FPS update rate


# Test function for development
if __name__ == "__main__":
    import sys
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create OLED manager (simulate if no hardware)
    oled = OLEDManager(simulate_display=True)
    
    print("Testing OLED Display Manager...")
    
    # Test splash screen
    print("Showing splash screen...")
    oled.show_splash_screen(3.0)
    
    # Test device selection
    print("Showing device selection...")
    oled.show_device_selection()
    time.sleep(2.0)
    
    # Test system info
    print("Showing system info...")
    oled.show_system_info(cpu_temp=45.2, memory_usage=67.3, battery_level=85.5)
    time.sleep(2.0)
    
    # Test GPS status
    print("Showing GPS status...")
    oled.show_gps_status(fix_type="RTK Fixed", lat=40.712776, lon=-74.005974, accuracy=0.02)
    time.sleep(2.0)
    
    print("OLED test complete!")
