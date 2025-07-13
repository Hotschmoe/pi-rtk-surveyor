#!/usr/bin/env python3
"""
Mock GPS Controller for Pi RTK Surveyor Testing
Provides simulated GPS data for development and testing
"""

import time
import threading
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging


class MockGPSController:
    """Mock GPS controller that simulates various GPS scenarios"""
    
    def __init__(self, scenario: str = "stationary"):
        """
        Initialize mock GPS controller
        
        Args:
            scenario: GPS scenario to simulate (stationary, moving, rtk_acquisition, poor_conditions)
        """
        self.scenario = scenario
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.current_position = None
        self.fix_type = 0
        self.satellites = 0
        self.accuracy = 99.9
        
        # Load scenario data
        self.nmea_data = self._load_scenario_data()
        self.data_index = 0
        
        # Position tracking
        self.lat = 0.0
        self.lon = 0.0
        self.elevation = 0.0
        
    def _load_scenario_data(self) -> List[str]:
        """Load NMEA data for the specified scenario"""
        scenario_files = {
            "stationary": "test-data/gps-samples/rtk-fixed.nmea",
            "moving": "test-data/gps-samples/moving-rover.nmea",
            "poor_conditions": "test-data/gps-samples/poor-conditions.nmea",
            "rtk_acquisition": "test-data/gps-samples/rtk-fixed.nmea"
        }
        
        file_path = scenario_files.get(self.scenario, scenario_files["stationary"])
        
        try:
            with open(file_path, 'r') as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        except FileNotFoundError:
            self.logger.warning(f"Scenario file not found: {file_path}, using default data")
            return self._generate_default_data()
    
    def _generate_default_data(self) -> List[str]:
        """Generate default NMEA data if scenario files not found"""
        return [
            "$GNGGA,123456.00,4012.34567,N,07401.23456,W,4,12,0.8,45.2,M,-33.2,M,1.2,0000*5A",
            "$GNRMC,123456.00,A,4012.34567,N,07401.23456,W,0.0,0.0,150324,,,A*73",
            "$GNVTG,0.0,T,0.0,M,0.0,N,0.0,K,A*13"
        ]
    
    def start(self):
        """Start the mock GPS controller"""
        self.running = True
        self.logger.info(f"Mock GPS controller started with scenario: {self.scenario}")
        
    def stop(self):
        """Stop the mock GPS controller"""
        self.running = False
        self.logger.info("Mock GPS controller stopped")
    
    def get_nmea_sentence(self) -> Optional[str]:
        """Get the next NMEA sentence from the scenario data"""
        if not self.running or not self.nmea_data:
            return None
            
        sentence = self.nmea_data[self.data_index]
        self.data_index = (self.data_index + 1) % len(self.nmea_data)
        
        # Update position from NMEA data
        self._parse_nmea_sentence(sentence)
        
        return sentence
    
    def _parse_nmea_sentence(self, sentence: str):
        """Parse NMEA sentence and update position data"""
        parts = sentence.split(',')
        
        if parts[0] == '$GNGGA':
            try:
                # Parse GGA sentence
                if len(parts) > 6 and parts[6]:
                    self.fix_type = int(parts[6])
                    
                if len(parts) > 7 and parts[7]:
                    self.satellites = int(parts[7])
                    
                if len(parts) > 8 and parts[8]:
                    self.accuracy = float(parts[8])
                    
                if len(parts) > 2 and parts[2]:
                    # Parse latitude
                    lat_str = parts[2]
                    lat_deg = float(lat_str[:2])
                    lat_min = float(lat_str[2:])
                    self.lat = lat_deg + lat_min / 60.0
                    if parts[3] == 'S':
                        self.lat = -self.lat
                        
                if len(parts) > 4 and parts[4]:
                    # Parse longitude
                    lon_str = parts[4]
                    lon_deg = float(lon_str[:3])
                    lon_min = float(lon_str[3:])
                    self.lon = lon_deg + lon_min / 60.0
                    if parts[5] == 'W':
                        self.lon = -self.lon
                        
                if len(parts) > 9 and parts[9]:
                    self.elevation = float(parts[9])
                    
            except (ValueError, IndexError):
                pass
    
    def get_position(self) -> Tuple[float, float, float]:
        """Get current position (lat, lon, elevation)"""
        return self.lat, self.lon, self.elevation
    
    def get_fix_type(self) -> int:
        """Get current GPS fix type"""
        return self.fix_type
    
    def get_satellites(self) -> int:
        """Get number of satellites in use"""
        return self.satellites
    
    def get_accuracy(self) -> float:
        """Get current position accuracy (HDOP)"""
        return self.accuracy
    
    def is_rtk_fixed(self) -> bool:
        """Check if GPS has RTK fixed solution"""
        return self.fix_type == 4
    
    def is_rtk_float(self) -> bool:
        """Check if GPS has RTK float solution"""
        return self.fix_type == 5
    
    def has_3d_fix(self) -> bool:
        """Check if GPS has 3D fix"""
        return self.fix_type >= 3


class MockRTKController:
    """Mock RTK controller for testing RTK functionality"""
    
    def __init__(self, mode: str = "base"):
        """
        Initialize mock RTK controller
        
        Args:
            mode: RTK mode (base or rover)
        """
        self.mode = mode
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.corrections_available = False
        self.base_position = (40.205761, -74.020576, 45.2)
        
    def start(self):
        """Start the mock RTK controller"""
        self.running = True
        self.logger.info(f"Mock RTK controller started in {self.mode} mode")
        
        if self.mode == "base":
            # Simulate base station providing corrections
            self.corrections_available = True
        
    def stop(self):
        """Stop the mock RTK controller"""
        self.running = False
        self.logger.info("Mock RTK controller stopped")
    
    def get_corrections(self) -> Optional[bytes]:
        """Get RTK corrections (mock RTCM3 data)"""
        if not self.running or self.mode != "base":
            return None
            
        # Mock RTCM3 correction data
        return b"\xd3\x00\x13\x3e\xd0\x00\x03\x8a\x0e\x44\x11\x41\x6a\x9f\x5a\x3c\x00\x00\x00\x00\x00\x00\x1d\x39\x87"
    
    def send_corrections(self, corrections: bytes) -> bool:
        """Send RTK corrections to rover"""
        if not self.running or self.mode != "rover":
            return False
            
        self.corrections_available = True
        return True
    
    def has_corrections(self) -> bool:
        """Check if RTK corrections are available"""
        return self.corrections_available


# Test function
if __name__ == "__main__":
    import sys
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Mock GPS Controller...")
    
    # Test stationary scenario
    print("\n1. Testing stationary scenario...")
    gps = MockGPSController("stationary")
    gps.start()
    
    for i in range(5):
        sentence = gps.get_nmea_sentence()
        print(f"NMEA: {sentence}")
        lat, lon, elev = gps.get_position()
        print(f"Position: {lat:.6f}, {lon:.6f}, {elev:.1f}")
        print(f"Fix: {gps.get_fix_type()}, Sats: {gps.get_satellites()}, Acc: {gps.get_accuracy()}")
        time.sleep(0.5)
    
    gps.stop()
    
    # Test RTK controller
    print("\n2. Testing RTK controller...")
    rtk = MockRTKController("base")
    rtk.start()
    
    corrections = rtk.get_corrections()
    print(f"Corrections: {corrections}")
    print(f"Has corrections: {rtk.has_corrections()}")
    
    rtk.stop()
    
    print("\nMock GPS test complete!") 