#!/usr/bin/env python3
"""
LC29H GNSS Controller for Pi RTK Surveyor
Handles communication with LC29H GNSS RTK HAT
"""

import time
import threading
import serial
from typing import Optional, Dict, List, Tuple, Callable
from enum import Enum
import logging
from pathlib import Path

try:
    import pynmea2
    PYNMEA2_AVAILABLE = True
except ImportError:
    PYNMEA2_AVAILABLE = False
    logging.warning("pynmea2 not available - using basic NMEA parsing")

class FixType(Enum):
    """GNSS fix types"""
    NO_FIX = 0
    GPS_FIX = 1
    DGPS_FIX = 2
    PPS_FIX = 3
    RTK_FIXED = 4
    RTK_FLOAT = 5
    ESTIMATED = 6
    MANUAL = 7
    SIMULATION = 8

class GNSSPosition:
    """GNSS position data structure"""
    
    def __init__(self):
        self.latitude = 0.0
        self.longitude = 0.0
        self.elevation = 0.0
        self.fix_type = FixType.NO_FIX
        self.satellites_used = 0
        self.hdop = 99.9
        self.vdop = 99.9
        self.pdop = 99.9
        self.accuracy_horizontal = 99.9
        self.accuracy_vertical = 99.9
        self.timestamp: Optional[float] = None
        self.valid = False
        
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'elevation': self.elevation,
            'fix_type': self.fix_type.value,
            'fix_type_name': self.fix_type.name,
            'satellites_used': self.satellites_used,
            'hdop': self.hdop,
            'vdop': self.vdop,
            'pdop': self.pdop,
            'accuracy_horizontal': self.accuracy_horizontal,
            'accuracy_vertical': self.accuracy_vertical,
            'timestamp': self.timestamp,
            'valid': self.valid
        }

class LC29HController:
    """LC29H GNSS HAT controller"""
    
    def __init__(self, port: str = '/dev/ttyAMA0', baudrate: int = 38400, simulate: bool = False):
        """
        Initialize LC29H controller
        
        Args:
            port: Serial port for GPS communication
            baudrate: Serial communication speed
            simulate: Use simulation mode for development
        """
        self.port = port
        self.baudrate = baudrate
        self.simulate = simulate
        self.logger = logging.getLogger(__name__)
        
        # Serial connection
        self.serial_connection = None
        self.connected = False
        
        # Position data
        self.current_position = GNSSPosition()
        self.position_callbacks = []
        
        # Threading
        self.running = False
        self.read_thread = None
        self.position_lock = threading.Lock()
        
        # NMEA parsing
        self.nmea_buffer = ""
        self.last_gga_time = 0
        self.last_rmc_time = 0
        
        # Statistics
        self.messages_received = 0
        self.parsing_errors = 0
        self.last_message_time = 0
        
        # Simulation data
        if self.simulate:
            self._init_simulation()
    
    def _init_simulation(self):
        """Initialize simulation mode"""
        self.logger.info("LC29H controller initialized in simulation mode")
        self.connected = True
        
        # Load mock GPS data if available
        try:
            from ..tests.mock_gps import MockGPSController
            self.mock_gps = MockGPSController("stationary")
            self.mock_gps.start()
            self.logger.info("Using mock GPS data for simulation")
        except ImportError:
            self.mock_gps = None
            self.logger.warning("Mock GPS not available - using basic simulation")
    
    def connect(self) -> bool:
        """
        Connect to LC29H GNSS module
        
        Returns:
            True if connection successful
        """
        if self.simulate:
            self.connected = True
            return True
            
        try:
            # Try common serial ports
            ports_to_try = [self.port, '/dev/ttyS0', '/dev/ttyUSB0', '/dev/ttyACM0']
            
            for port in ports_to_try:
                try:
                    self.logger.info(f"Attempting to connect to GPS on {port}")
                    self.serial_connection = serial.Serial(
                        port=port,
                        baudrate=self.baudrate,
                        timeout=1.0,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS
                    )
                    
                    # Test connection by reading some data
                    self.logger.info(f"Testing GPS connection on {port} at {self.baudrate} baud...")
                    time.sleep(3)  # Allow more time for GPS to send data
                    
                    bytes_waiting = self.serial_connection.in_waiting
                    self.logger.debug(f"Bytes waiting on {port}: {bytes_waiting}")
                    
                    if bytes_waiting > 0:
                        test_data = self.serial_connection.read(bytes_waiting)
                        self.logger.debug(f"Raw data from {port}: {test_data[:100]}")  # Show first 100 bytes
                        
                        if b'$' in test_data:  # NMEA sentences start with $
                            self.port = port
                            self.connected = True
                            self.logger.info(f"Successfully connected to GPS on {port} - NMEA data detected")
                            return True
                        else:
                            self.logger.warning(f"Data received on {port} but no NMEA sentences detected")
                    else:
                        self.logger.warning(f"No data received on {port} after 3 seconds")
                    
                    self.serial_connection.close()
                    
                except serial.SerialException:
                    continue
            
            self.logger.error("Failed to connect to GPS on any port")
            return False
            
        except Exception as e:
            self.logger.error(f"GPS connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from GPS module"""
        self.stop()
        
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            
        if self.simulate and self.mock_gps:
            self.mock_gps.stop()
            
        self.connected = False
        self.logger.info("GPS disconnected")
    
    def start(self) -> bool:
        """
        Start GPS data reading
        
        Returns:
            True if started successfully
        """
        if self.running:
            return True
            
        if not self.connected:
            if not self.connect():
                return False
        
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        
        self.logger.info("GPS data reading started")
        return True
    
    def stop(self):
        """Stop GPS data reading"""
        self.running = False
        
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2.0)
            
        self.logger.info("GPS data reading stopped")
    
    def _read_loop(self):
        """Main GPS data reading loop"""
        while self.running:
            try:
                if self.simulate:
                    self._simulate_gps_data()
                else:
                    self._read_serial_data()
                    
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                
            except Exception as e:
                self.logger.error(f"GPS reading error: {e}")
                time.sleep(1.0)  # Wait before retrying
    
    def _simulate_gps_data(self):
        """Simulate GPS data for development"""
        if self.mock_gps:
            # Use mock GPS data
            sentence = self.mock_gps.get_nmea_sentence()
            if sentence:
                self._process_nmea_sentence(sentence)
        else:
            # Basic simulation
            self._simulate_basic_position()
    
    def _simulate_basic_position(self):
        """Basic position simulation"""
        current_time = time.time()
        
        # Simulate RTK fixed position with small random variations
        base_lat = 40.205761
        base_lon = -74.020576
        base_elev = 45.2
        
        # Add small random variations (±1 meter)
        import random
        lat_variation = random.uniform(-0.00001, 0.00001)  # ~1m in latitude
        lon_variation = random.uniform(-0.00001, 0.00001)  # ~1m in longitude
        elev_variation = random.uniform(-0.5, 0.5)  # ±0.5m elevation
        
        with self.position_lock:
            self.current_position.latitude = base_lat + lat_variation
            self.current_position.longitude = base_lon + lon_variation
            self.current_position.elevation = base_elev + elev_variation
            self.current_position.fix_type = FixType.RTK_FIXED
            self.current_position.satellites_used = 12
            self.current_position.hdop = 0.8
            self.current_position.accuracy_horizontal = 0.02
            self.current_position.accuracy_vertical = 0.03
            self.current_position.valid = True
            self.current_position.timestamp = current_time
        
        # Trigger callbacks
        self._trigger_position_callbacks()
    
    def _read_serial_data(self):
        """Read data from serial connection"""
        if not self.serial_connection or not self.serial_connection.is_open:
            return
            
        try:
            # Read available data
            if self.serial_connection.in_waiting > 0:
                data = self.serial_connection.read(self.serial_connection.in_waiting)
                self.nmea_buffer += data.decode('ascii', errors='ignore')
                
                # Process complete NMEA sentences
                while '\n' in self.nmea_buffer:
                    line, self.nmea_buffer = self.nmea_buffer.split('\n', 1)
                    line = line.strip()
                    
                    if line.startswith('$') and len(line) > 10:
                        self._process_nmea_sentence(line)
                        
        except Exception as e:
            self.logger.error(f"Serial reading error: {e}")
    
    def _process_nmea_sentence(self, sentence: str):
        """Process NMEA sentence"""
        try:
            self.messages_received += 1
            self.last_message_time = time.time()
            
            # Parse with pynmea2 if available
            if PYNMEA2_AVAILABLE:
                self._parse_with_pynmea2(sentence)
            else:
                self._parse_basic_nmea(sentence)
                
        except Exception as e:
            self.parsing_errors += 1
            self.logger.debug(f"NMEA parsing error: {e}")
    
    def _parse_with_pynmea2(self, sentence: str):
        """Parse NMEA using pynmea2 library"""
        try:
            msg = pynmea2.parse(sentence)
            
            with self.position_lock:
                if isinstance(msg, pynmea2.GGA):
                    # Global Positioning System Fix Data
                    if msg.latitude and msg.longitude:
                        self.current_position.latitude = float(msg.latitude)
                        self.current_position.longitude = float(msg.longitude)
                        
                    if msg.altitude:
                        self.current_position.elevation = float(msg.altitude)
                        
                    if msg.gps_qual is not None:
                        self.current_position.fix_type = FixType(int(msg.gps_qual))
                        
                    if msg.num_sats:
                        self.current_position.satellites_used = int(msg.num_sats)
                        
                    if msg.horizontal_dil:
                        self.current_position.hdop = float(msg.horizontal_dil)
                        
                    self.current_position.valid = msg.gps_qual is not None and int(msg.gps_qual) > 0
                    self.current_position.timestamp = time.time()
                    
                    self.last_gga_time = time.time()
                    self._trigger_position_callbacks()
                    
                elif isinstance(msg, pynmea2.RMC):
                    # Recommended Minimum Navigation Information
                    if msg.latitude and msg.longitude:
                        self.current_position.latitude = float(msg.latitude)
                        self.current_position.longitude = float(msg.longitude)
                        
                    self.current_position.valid = msg.status == 'A'
                    self.current_position.timestamp = time.time()
                    self.last_rmc_time = time.time()
                    
        except Exception as e:
            self.logger.debug(f"pynmea2 parsing error: {e}")
    
    def _parse_basic_nmea(self, sentence: str):
        """Basic NMEA parsing without external library"""
        parts = sentence.split(',')
        
        if not parts or len(parts) < 3:
            return
            
        sentence_type = parts[0]
        
        with self.position_lock:
            if sentence_type.endswith('GGA') and len(parts) >= 15:
                # $GNGGA sentence - Global Positioning System Fix Data
                try:
                    if parts[2] and parts[4]:  # Latitude and longitude
                        lat = self._parse_coordinate(parts[2], parts[3])
                        lon = self._parse_coordinate(parts[4], parts[5])
                        
                        if lat is not None and lon is not None:
                            self.current_position.latitude = lat
                            self.current_position.longitude = lon
                    
                    if parts[6]:  # Fix quality
                        self.current_position.fix_type = FixType(int(parts[6]))
                        
                    if parts[7]:  # Number of satellites
                        self.current_position.satellites_used = int(parts[7])
                        
                    if parts[8]:  # HDOP
                        self.current_position.hdop = float(parts[8])
                        
                    if parts[9]:  # Altitude
                        self.current_position.elevation = float(parts[9])
                        
                    self.current_position.valid = bool(parts[6] and int(parts[6]) > 0)
                    self.current_position.timestamp = time.time()
                    
                    self.last_gga_time = time.time()
                    self._trigger_position_callbacks()
                    
                except (ValueError, IndexError):
                    pass
                    
            elif sentence_type.endswith('RMC') and len(parts) >= 12:
                # $GNRMC sentence - Recommended Minimum Navigation Information
                try:
                    if parts[3] and parts[5]:  # Latitude and longitude
                        lat = self._parse_coordinate(parts[3], parts[4])
                        lon = self._parse_coordinate(parts[5], parts[6])
                        
                        if lat is not None and lon is not None:
                            self.current_position.latitude = lat
                            self.current_position.longitude = lon
                            
                    self.current_position.valid = parts[2] == 'A'
                    self.current_position.timestamp = time.time()
                    self.last_rmc_time = time.time()
                    
                except (ValueError, IndexError):
                    pass
    
    def _parse_coordinate(self, coord_str: str, direction: str) -> Optional[float]:
        """Parse NMEA coordinate format to decimal degrees"""
        try:
            if not coord_str or not direction:
                return None
                
            # NMEA format: DDMM.MMMMM or DDDMM.MMMMM
            if '.' not in coord_str:
                return None
                
            decimal_pos = coord_str.index('.')
            
            if decimal_pos < 3:  # Invalid format
                return None
                
            # Extract degrees and minutes
            degrees = int(coord_str[:decimal_pos-2])
            minutes = float(coord_str[decimal_pos-2:])
            
            # Convert to decimal degrees
            decimal_degrees = degrees + minutes / 60.0
            
            # Apply direction
            if direction in ['S', 'W']:
                decimal_degrees = -decimal_degrees
                
            return decimal_degrees
            
        except (ValueError, IndexError):
            return None
    
    def _trigger_position_callbacks(self):
        """Trigger registered position callbacks"""
        for callback in self.position_callbacks:
            try:
                callback(self.current_position)
            except Exception as e:
                self.logger.error(f"Position callback error: {e}")
    
    def get_position(self) -> GNSSPosition:
        """Get current position"""
        with self.position_lock:
            return self.current_position
    
    def get_position_dict(self) -> Dict:
        """Get current position as dictionary"""
        return self.get_position().to_dict()
    
    def is_position_valid(self) -> bool:
        """Check if current position is valid"""
        with self.position_lock:
            return self.current_position.valid and self.current_position.fix_type != FixType.NO_FIX
    
    def has_rtk_fix(self) -> bool:
        """Check if GPS has RTK fixed solution"""
        with self.position_lock:
            return self.current_position.fix_type == FixType.RTK_FIXED
    
    def has_rtk_float(self) -> bool:
        """Check if GPS has RTK float solution"""
        with self.position_lock:
            return self.current_position.fix_type == FixType.RTK_FLOAT
    
    def get_accuracy(self) -> Tuple[float, float]:
        """Get horizontal and vertical accuracy"""
        with self.position_lock:
            return (self.current_position.accuracy_horizontal, 
                    self.current_position.accuracy_vertical)
    
    def register_position_callback(self, callback: Callable[[GNSSPosition], None]):
        """Register callback for position updates"""
        self.position_callbacks.append(callback)
        
    def unregister_position_callback(self, callback: Callable[[GNSSPosition], None]):
        """Unregister position callback"""
        if callback in self.position_callbacks:
            self.position_callbacks.remove(callback)
    
    def get_statistics(self) -> Dict:
        """Get GPS statistics"""
        return {
            'messages_received': self.messages_received,
            'parsing_errors': self.parsing_errors,
            'error_rate': self.parsing_errors / max(1, self.messages_received),
            'last_message_time': self.last_message_time,
            'time_since_last_message': time.time() - self.last_message_time if self.last_message_time > 0 else 0,
            'last_gga_time': self.last_gga_time,
            'last_rmc_time': self.last_rmc_time,
            'connected': self.connected,
            'running': self.running
        }
    
    def send_command(self, command: str) -> bool:
        """
        Send command to GPS module
        
        Args:
            command: NMEA command to send
            
        Returns:
            True if command sent successfully
        """
        if self.simulate:
            self.logger.info(f"Simulated GPS command: {command}")
            return True
            
        if not self.serial_connection or not self.serial_connection.is_open:
            return False
            
        try:
            command_bytes = f"{command}\r\n".encode('ascii')
            self.serial_connection.write(command_bytes)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send GPS command: {e}")
            return False


# Test function for development
if __name__ == "__main__":
    import sys
    
    # Set up logging
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("Testing LC29H GPS Controller...")
    
    # Create GPS controller in simulation mode
    gps = LC29HController(simulate=True)
    
    # Position update callback
    def position_callback(position: GNSSPosition):
        print(f"Position update: {position.latitude:.6f}, {position.longitude:.6f}, "
              f"{position.elevation:.1f}m - {position.fix_type.name}")
    
    # Register callback
    gps.register_position_callback(position_callback)
    
    # Start GPS
    if gps.start():
        print("GPS started successfully")
        
        try:
            # Monitor for 10 seconds
            for i in range(10):
                time.sleep(1)
                pos = gps.get_position()
                stats = gps.get_statistics()
                
                print(f"Status: Valid={pos.valid}, Fix={pos.fix_type.name}, "
                      f"Sats={pos.satellites_used}, HDOP={pos.hdop:.1f}")
                print(f"Stats: Messages={stats['messages_received']}, "
                      f"Errors={stats['parsing_errors']}")
                
        except KeyboardInterrupt:
            print("\nTest interrupted")
            
    else:
        print("Failed to start GPS")
    
    # Cleanup
    gps.stop()
    gps.disconnect()
    print("GPS controller test complete!")
