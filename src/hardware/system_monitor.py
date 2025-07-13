#!/usr/bin/env python3
"""
System Monitor for Pi RTK Surveyor
Monitors CPU temperature, memory usage, battery level, and system health
"""

import time
import logging
from typing import Dict, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class SystemMonitor:
    """Monitors system health and resource usage"""
    
    def __init__(self):
        """Initialize system monitor"""
        self.logger = logging.getLogger(__name__)
        self.last_update = 0
        self.update_interval = 1.0  # Update every second
        self.cached_info = {}
        
        if not PSUTIL_AVAILABLE:
            self.logger.warning("psutil not available - system monitoring limited")
        
    def get_system_info(self) -> Dict[str, float]:
        """Get current system information"""
        current_time = time.time()
        
        # Return cached info if updated recently
        if current_time - self.last_update < self.update_interval:
            return self.cached_info
            
        info = {
            'cpu_temp': self._get_cpu_temperature(),
            'memory_percent': self._get_memory_usage(),
            'cpu_percent': self._get_cpu_usage(),
            'disk_usage': self._get_disk_usage(),
            'battery_level': self._get_battery_level(),
            'uptime': self._get_uptime()
        }
        
        self.cached_info = info
        self.last_update = current_time
        
        return info
        
    def _get_cpu_temperature(self) -> float:
        """Get CPU temperature in Celsius"""
        try:
            # Try to read from Raspberry Pi thermal sensor
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_str = f.read().strip()
                temp_celsius = float(temp_str) / 1000.0
                return temp_celsius
        except (FileNotFoundError, ValueError, PermissionError):
            # Fallback: try psutil if available
            if PSUTIL_AVAILABLE:
                try:
                    temps = psutil.sensors_temperatures()
                    if 'cpu_thermal' in temps:
                        return temps['cpu_thermal'][0].current
                    elif temps:
                        # Return first available temperature sensor
                        return list(temps.values())[0][0].current
                except:
                    pass
            
            # Unable to read temperature
            self.logger.warning("Unable to read CPU temperature")
            return 0.0
            
    def _get_memory_usage(self) -> float:
        """Get memory usage percentage"""
        if not PSUTIL_AVAILABLE:
            self.logger.warning("psutil not available for memory monitoring")
            return 0.0
            
        try:
            memory = psutil.virtual_memory()
            return memory.percent
        except:
            self.logger.warning("Failed to read memory usage")
            return 0.0
            
    def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage"""
        if not PSUTIL_AVAILABLE:
            self.logger.warning("psutil not available for CPU monitoring")
            return 0.0
            
        try:
            return psutil.cpu_percent(interval=0.1)
        except:
            self.logger.warning("Failed to read CPU usage")
            return 0.0
            
    def _get_disk_usage(self) -> float:
        """Get disk usage percentage"""
        if not PSUTIL_AVAILABLE:
            self.logger.warning("psutil not available for disk monitoring")
            return 0.0
            
        try:
            disk = psutil.disk_usage('/')
            return (disk.used / disk.total) * 100
        except:
            self.logger.warning("Failed to read disk usage")
            return 0.0
            
    def _get_battery_level(self) -> float:
        """Get battery level percentage"""
        # For Pi with UPS HAT or power bank, this would read from I2C
        # TODO: Implement actual battery monitoring based on hardware
        try:
            # Try to read from UPS HAT if available
            # This is a placeholder - actual implementation depends on UPS hardware
            # For now, check if we have a battery sensor
            if PSUTIL_AVAILABLE:
                battery = psutil.sensors_battery()
                if battery:
                    return battery.percent
        except:
            pass
            
        # No battery monitoring available
        self.logger.debug("No battery monitoring available")
        return 100.0  # Assume wall power
            
    def _get_uptime(self) -> float:
        """Get system uptime in seconds"""
        if not PSUTIL_AVAILABLE:
            try:
                # Fallback: read from /proc/uptime
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.readline().split()[0])
                    return uptime_seconds
            except:
                self.logger.warning("Unable to read system uptime")
                return 0.0
            
        try:
            return time.time() - psutil.boot_time()
        except:
            self.logger.warning("Failed to calculate uptime")
            return 0.0
            
    def get_formatted_info(self) -> Dict[str, str]:
        """Get system info formatted as strings for display"""
        info = self.get_system_info()
        
        return {
            'cpu_temp': f"{info['cpu_temp']:.1f}°C",
            'memory': f"{info['memory_percent']:.1f}%",
            'cpu': f"{info['cpu_percent']:.1f}%", 
            'disk': f"{info['disk_usage']:.1f}%",
            'battery': f"{info['battery_level']:.1f}%",
            'uptime': self._format_uptime(info['uptime'])
        }
        
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human readable format"""
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def log_system_status(self):
        """Log current system status"""
        info = self.get_formatted_info()
        self.logger.info(f"System Status - "
                        f"CPU: {info['cpu_temp']}, "
                        f"Memory: {info['memory']}, "
                        f"Disk: {info['disk']}, "
                        f"Battery: {info['battery']}, "
                        f"Uptime: {info['uptime']}")
