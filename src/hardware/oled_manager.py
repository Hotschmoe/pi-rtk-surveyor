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

from .gpio_manager import get_gpio_manager, PinMode, PinPull

try:
    from luma.core.interface.serial import spi
    from luma.core.render import canvas
    from luma.oled.device import sh1106
    DISPLAY_AVAILABLE = True
except ImportError:
    DISPLAY_AVAILABLE = False

class OLEDManager:
    """Manages OLED display operations for Pi RTK Surveyor"""
    
    def __init__(self):
        """Initialize OLED display manager"""
        self.device = None
        self.display_thread = None
        self.running = False
        self.current_screen = None
        self.brightness = 255  # 0-255
        
        # Display dimensions (Waveshare 1.3" OLED)
        self.width = 128
        self.height = 64
        
        # Set up logging first (needed by _init_display)
        self.logger = logging.getLogger(__name__)
        
        if not DISPLAY_AVAILABLE:
            self.logger.error("OLED display libraries not available")
            raise RuntimeError("OLED display libraries not available")
        
        # Get GPIO manager and register component
        self.gpio_manager = get_gpio_manager()
        self.component_name = "oled_manager"
        
        # Initialize display
        self._init_display()
        
    def _init_display(self):
        """Initialize the physical OLED display"""
        try:
            # Register with GPIO manager
            if not self.gpio_manager.register_component(self.component_name):
                self.logger.error("Failed to register with GPIO manager")
                raise RuntimeError("OLED manager registration failed")
            
            # Request OLED pins through GPIO manager
            # Note: The luma.oled library will handle the actual GPIO setup,
            # but we need to reserve the pins to prevent conflicts
            if not self.gpio_manager.request_oled_pins(self.component_name):
                self.logger.error("Failed to allocate OLED pins")
                raise RuntimeError("OLED pin allocation failed")
            
            # Initialize the luma.oled device
            # Waveshare 1.3" OLED uses SH1106 controller
            serial = spi(device=0, port=0)
            self.device = sh1106(serial, width=self.width, height=self.height)
            self.device.contrast(self.brightness)
            self.logger.info("OLED display initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OLED display: {e}")
            raise RuntimeError(f"OLED display initialization failed: {e}")
            
    def cleanup(self):
        """Clean up OLED display resources"""
        if self.device:
            try:
                self.device.cleanup()
                self.logger.debug("OLED device cleaned up")
            except Exception as e:
                self.logger.warning(f"Error cleaning up OLED device: {e}")
        
        # Unregister from GPIO manager
        self.gpio_manager.unregister_component(self.component_name)
        self.logger.info("OLED manager cleaned up")
            
    def show_splash_screen(self, duration: float = 3.0):
        """Display startup splash screen"""
        def draw_splash(draw, width, height):
            # Clear screen
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            
            try:
                # Try to load system fonts
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
                font_subtitle = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                font_version = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                # Fallback to default font
                font_title = ImageFont.load_default()
                font_subtitle = ImageFont.load_default()
                font_version = ImageFont.load_default()
            
            # Main title
            title = "Pi RTK"
            title_bbox = draw.textbbox((0, 0), title, font=font_title)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text(((width - title_width) // 2, 5), title, font=font_title, fill=255)
            
            # Subtitle
            subtitle = "Surveyor"
            subtitle_bbox = draw.textbbox((0, 0), subtitle, font=font_subtitle)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
            draw.text(((width - subtitle_width) // 2, 25), subtitle, font=font_subtitle, fill=255)
            
            # Version
            version = "v1.0"
            version_bbox = draw.textbbox((0, 0), version, font=font_version)
            version_width = version_bbox[2] - version_bbox[0]
            draw.text(((width - version_width) // 2, 45), version, font=font_version, fill=255)
            
            # Loading indicator
            loading = "Loading..."
            loading_bbox = draw.textbbox((0, 0), loading, font=font_version)
            loading_width = loading_bbox[2] - loading_bbox[0]
            draw.text(((width - loading_width) // 2, 55), loading, font=font_version, fill=255)
        
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

    def show_base_init_screen(self, init_step: str, status: str = ""):
        """Display base station initialization screen"""
        def draw_base_init(draw, width, height):
            # Clear screen
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            
            try:
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
                font_status = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                font_title = ImageFont.load_default()
                font_status = ImageFont.load_default()
            
            # Title
            title = "BASE STATION"
            title_bbox = draw.textbbox((0, 0), title, font=font_title)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text(((width - title_width) // 2, 5), title, font=font_title, fill=255)
            
            # Current step
            step_text = f"Step: {init_step}"
            draw.text((5, 25), step_text, font=font_status, fill=255)
            
            # Status
            if status:
                draw.text((5, 40), status, font=font_status, fill=255)
            
            # Loading indicator
            loading = "Initializing..."
            loading_bbox = draw.textbbox((0, 0), loading, font=font_status)
            loading_width = loading_bbox[2] - loading_bbox[0]
            draw.text(((width - loading_width) // 2, 55), loading, font=font_status, fill=255)
        
        self._display_content(draw_base_init)

    def show_rover_init_screen(self, init_step: str, status: str = ""):
        """Display rover initialization screen"""
        def draw_rover_init(draw, width, height):
            # Clear screen
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            
            try:
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
                font_status = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                font_title = ImageFont.load_default()
                font_status = ImageFont.load_default()
            
            # Title
            title = "ROVER"
            title_bbox = draw.textbbox((0, 0), title, font=font_title)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text(((width - title_width) // 2, 5), title, font=font_title, fill=255)
            
            # Current step
            step_text = f"Step: {init_step}"
            draw.text((5, 25), step_text, font=font_status, fill=255)
            
            # Status
            if status:
                draw.text((5, 40), status, font=font_status, fill=255)
            
            # Loading indicator
            loading = "Connecting..."
            loading_bbox = draw.textbbox((0, 0), loading, font=font_status)
            loading_width = loading_bbox[2] - loading_bbox[0]
            draw.text(((width - loading_width) // 2, 55), loading, font=font_status, fill=255)
        
        self._display_content(draw_rover_init)

    def show_base_monitoring(self, satellites: int, rovers_connected: int, 
                           battery_level: float, uptime: str, points_logged: int):
        """Display base station monitoring information"""
        def draw_base_monitor(draw, width, height):
            # Clear screen
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            
            try:
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
                font_info = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
            except:
                font_title = ImageFont.load_default()
                font_info = ImageFont.load_default()
            
            # Title
            title = "BASE STATION"
            title_bbox = draw.textbbox((0, 0), title, font=font_title)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text(((width - title_width) // 2, 2), title, font=font_title, fill=255)
            
            # Monitoring info
            sat_text = f"SATs: {satellites}"
            rovers_text = f"Rovers: {rovers_connected}"
            battery_text = f"Batt: {battery_level:.1f}%"
            uptime_text = f"Up: {uptime}"
            points_text = f"Points: {points_logged}"
            
            draw.text((2, 16), sat_text, font=font_info, fill=255)
            draw.text((65, 16), rovers_text, font=font_info, fill=255)
            draw.text((2, 28), battery_text, font=font_info, fill=255)
            draw.text((65, 28), uptime_text, font=font_info, fill=255)
            draw.text((2, 40), points_text, font=font_info, fill=255)
            
            # Status indicators
            # Satellite status
            sat_color = 255 if satellites >= 4 else 128
            draw.rectangle((120, 16, 126, 22), outline=255, fill=sat_color)
            
            # Battery status
            batt_color = 255 if battery_level > 20 else 128
            draw.rectangle((120, 28, 126, 34), outline=255, fill=batt_color)
            
            # Bottom status line
            status = f"Base Ready - KEY1:Menu"
            draw.text((2, 52), status, font=font_info, fill=255)
        
        self._display_content(draw_base_monitor)

    def show_rover_monitoring(self, satellites: int, base_connected: bool, 
                            signal_strength: int, battery_level: float, 
                            uptime: str, point_ready: bool = False):
        """Display rover monitoring information"""
        def draw_rover_monitor(draw, width, height):
            # Clear screen
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            
            try:
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
                font_info = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
            except:
                font_title = ImageFont.load_default()
                font_info = ImageFont.load_default()
            
            # Title
            title = "ROVER"
            title_bbox = draw.textbbox((0, 0), title, font=font_title)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text(((width - title_width) // 2, 2), title, font=font_title, fill=255)
            
            # Monitoring info
            sat_text = f"SATs: {satellites}"
            base_text = f"Base: {'OK' if base_connected else 'NO'}"
            signal_text = f"Signal: {signal_strength}%"
            battery_text = f"Batt: {battery_level:.1f}%"
            uptime_text = f"Up: {uptime}"
            
            draw.text((2, 16), sat_text, font=font_info, fill=255)
            draw.text((65, 16), base_text, font=font_info, fill=255)
            draw.text((2, 28), signal_text, font=font_info, fill=255)
            draw.text((65, 28), battery_text, font=font_info, fill=255)
            draw.text((2, 40), uptime_text, font=font_info, fill=255)
            
            # Status indicators
            # Satellite status
            sat_color = 255 if satellites >= 4 else 128
            draw.rectangle((120, 16, 126, 22), outline=255, fill=sat_color)
            
            # Base connection status
            base_color = 255 if base_connected else 64
            draw.rectangle((120, 28, 126, 34), outline=255, fill=base_color)
            
            # Battery status
            batt_color = 255 if battery_level > 20 else 128
            draw.rectangle((120, 40, 126, 46), outline=255, fill=batt_color)
            
            # Bottom status line
            if point_ready:
                status = "Ready - KEY3:Log Point"
            else:
                status = "Rover Ready - KEY1:Menu"
            draw.text((2, 52), status, font=font_info, fill=255)
        
        self._display_content(draw_rover_monitor)
        
    def show_system_info(self, cpu_temp: float, memory_usage: float, battery_level: float):
        """Display system information"""
        def draw_system(draw, width, height):
            # Clear screen
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            
            try:
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
                font_info = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                font_title = ImageFont.load_default()
                font_info = ImageFont.load_default()
            
            # Title
            title = "System Info"
            title_bbox = draw.textbbox((0, 0), title, font=font_title)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text(((width - title_width) // 2, 2), title, font=font_title, fill=255)
            
            # System information
            temp_text = f"CPU: {cpu_temp:.1f}°C"
            mem_text = f"Memory: {memory_usage:.1f}%"
            batt_text = f"Battery: {battery_level:.1f}%"
            
            draw.text((5, 18), temp_text, font=font_info, fill=255)
            draw.text((5, 32), mem_text, font=font_info, fill=255)
            draw.text((5, 46), batt_text, font=font_info, fill=255)
        
        self._display_content(draw_system)
        
    def show_gps_status(self, fix_type: str, lat: float, lon: float, accuracy: float):
        """Display GPS status information"""
        def draw_gps(draw, width, height):
            # Clear screen
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            
            try:
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
                font_info = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
                font_coords = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
            except:
                font_title = ImageFont.load_default()
                font_info = ImageFont.load_default()
                font_coords = ImageFont.load_default()
            
            # Title with fix type
            title = f"GPS: {fix_type}"
            title_bbox = draw.textbbox((0, 0), title, font=font_title)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text(((width - title_width) // 2, 2), title, font=font_title, fill=255)
            
            # Coordinates
            lat_text = f"Lat: {lat:.6f}"
            lon_text = f"Lon: {lon:.6f}"
            acc_text = f"Acc: ±{accuracy:.2f}m"
            
            draw.text((2, 18), lat_text, font=font_coords, fill=255)
            draw.text((2, 30), lon_text, font=font_coords, fill=255)
            draw.text((2, 42), acc_text, font=font_info, fill=255)
            
            # Status indicator
            status_color = 255 if accuracy < 1.0 else 128
            draw.rectangle((width-10, 50, width-2, 58), outline=255, fill=status_color)
        
        self._display_content(draw_gps)
    
    def clear_display(self):
        """Clear the display"""
        if self.device:
            self.device.clear()
    
    def _display_content(self, draw_function: Callable, duration: Optional[float] = None):
        """Display content using the provided draw function"""
        if not self.device:
            self.logger.warning("No display device available")
            return
            
        try:
            with canvas(self.device) as draw:
                draw_function(draw, self.width, self.height)
            
            if duration:
                time.sleep(duration)
                
        except Exception as e:
            self.logger.error(f"Error displaying content: {e}")
