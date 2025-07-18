#!/usr/bin/env python3
"""
Flask Web Server for Pi RTK Surveyor Base Station
Provides real-time monitoring, configuration, and data visualization
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

# Add src directory to Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

# Import RTK Surveyor modules
from common.lc29h_controller import LC29HController, GNSSPosition, FixType
from hardware.system_monitor import SystemMonitor

# Optional imports
try:
    from hardware.battery_monitor import BatteryMonitor
except ImportError:
    BatteryMonitor = type(None)

class RTKWebServer:
    """Flask web server for RTK base station monitoring"""
    
    def __init__(self, gps_controller: Optional[LC29HController] = None, 
                 system_monitor: Optional[SystemMonitor] = None,
                 battery_monitor: Optional[Any] = None,
                 host: str = '0.0.0.0', port: int = 5000):
        """
        Initialize RTK Web Server
        
        Args:
            gps_controller: GPS controller instance for position data
            system_monitor: System monitor for hardware stats
            battery_monitor: Battery monitor for power management
            host: Server host address (0.0.0.0 for all interfaces)
            port: Server port number
        """
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__)
        
        # Component references
        self.gps_controller = gps_controller
        self.system_monitor = system_monitor
        self.battery_monitor = battery_monitor
        
        # Check if template and static directories exist
        template_dir = Path(__file__).parent / 'templates'
        static_dir = Path(__file__).parent / 'static'
        
        # Create directories if they don't exist
        template_dir.mkdir(exist_ok=True)
        static_dir.mkdir(exist_ok=True)
        
        # Flask app setup with fallback for missing templates
        self.app = Flask(__name__, 
                        template_folder=str(template_dir),
                        static_folder=str(static_dir))
        self.app.config['SECRET_KEY'] = 'pi-rtk-surveyor-secret'
        
        # Disable Flask's default logger to reduce noise
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        
        try:
            self.socketio = SocketIO(self.app, cors_allowed_origins="*", logger=False, engineio_logger=False)
        except Exception as e:
            self.logger.error(f"Failed to initialize SocketIO: {e}")
            self.socketio = None
        
        # Server state
        self.running = False
        self.update_thread = None
        self.connected_clients = set()
        self.server_thread = None
        
        # Data storage
        self.position_history = []
        self.max_position_history = 100
        self.system_stats_history = []
        self.max_stats_history = 50
        
        # Configuration
        self.config = {
            'device_mode': 'base_station',
            'rtk_enabled': True,
            'logging_enabled': False,
            'auto_logging': False,
            'log_interval': 1.0,  # seconds
            'correction_broadcast': True,
            'correction_port': 2101,
            'position_threshold': 0.1,  # meters
            'elevation_mask': 10,  # degrees
            'update_rate': 1.0  # Hz
        }
        
        self._setup_routes()
        self._setup_socketio_events()
        
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main dashboard page"""
            return render_template('dashboard.html')
            
        @self.app.route('/config')
        def config_page():
            """Configuration management page"""
            return render_template('config.html')
            
        @self.app.route('/data')
        def data_page():
            """Data visualization page"""
            return render_template('data.html')
            
        @self.app.route('/logs')
        def logs_page():
            """System logs page"""
            return render_template('logs.html')
            
        # API Routes
        @self.app.route('/api/status')
        def api_status():
            """Get current system status"""
            return jsonify(self._get_system_status())
            
        @self.app.route('/api/gps')
        def api_gps():
            """Get current GPS position"""
            return jsonify(self._get_gps_data())
            
        @self.app.route('/api/config', methods=['GET', 'POST'])
        def api_config():
            """Get or update configuration"""
            if request.method == 'GET':
                return jsonify(self.config)
            else:
                # Update configuration
                new_config = request.json
                self.config.update(new_config)
                self._save_config()
                return jsonify({'status': 'success', 'config': self.config})
                
        @self.app.route('/api/position-history')
        def api_position_history():
            """Get position history for visualization"""
            return jsonify(self.position_history)
            
        @self.app.route('/api/system-stats')
        def api_system_stats():
            """Get system statistics history"""
            return jsonify(self.system_stats_history)
            
        @self.app.route('/api/control/<action>', methods=['POST'])
        def api_control(action):
            """Control base station operations"""
            return jsonify(self._handle_control_action(action))
            
    def _setup_socketio_events(self):
        """Setup SocketIO events for real-time updates"""
        
        if not self.socketio:
            self.logger.warning("SocketIO not available, skipping event setup")
            return
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            self.logger.info(f"Client connected: {request.sid}")
            self.connected_clients.add(request.sid)
            
            # Send initial data
            emit('status_update', self._get_system_status())
            emit('gps_update', self._get_gps_data())
            
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            self.logger.info(f"Client disconnected: {request.sid}")
            self.connected_clients.discard(request.sid)
            
        @self.socketio.on('request_update')
        def handle_request_update():
            """Handle client request for immediate update"""
            emit('status_update', self._get_system_status())
            emit('gps_update', self._get_gps_data())
            
    def _get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'device_mode': self.config['device_mode'],
            'rtk_enabled': self.config['rtk_enabled'],
            'logging_enabled': self.config['logging_enabled'],
            'uptime': time.time() - getattr(self, 'start_time', time.time()),
            'connected_clients': len(self.connected_clients)
        }
        
        # Add system monitor data
        if self.system_monitor:
            sys_info = self.system_monitor.get_system_info()
            status.update({
                'cpu_temp': sys_info.get('cpu_temp', 0),
                'cpu_usage': sys_info.get('cpu_percent', 0),
                'memory_usage': sys_info.get('memory_percent', 0),
                'disk_usage': sys_info.get('disk_percent', 0),
                'load_average': sys_info.get('load_avg', [0, 0, 0])
            })
            
        # Add battery monitor data
        if self.battery_monitor:
            battery_info = self.battery_monitor.get_battery_info()
            status.update({
                'battery_level': battery_info.get('percentage', 100),
                'battery_voltage': battery_info.get('voltage', 0),
                'charging': battery_info.get('charging', False),
                'estimated_runtime': battery_info.get('estimated_runtime', 0)
            })
            
        return status
        
    def _get_gps_data(self) -> Dict[str, Any]:
        """Get current GPS data"""
        if not self.gps_controller:
            return {
                'connected': False,
                'position': None,
                'statistics': {}
            }
            
        position = self.gps_controller.get_position()
        
        return {
            'connected': self.gps_controller.connected,
            'position': position.to_dict() if position else None,
            'statistics': self.gps_controller.get_statistics(),
            'rtk_fixed': self.gps_controller.has_rtk_fix(),
            'rtk_float': self.gps_controller.has_rtk_float(),
            'accuracy': self.gps_controller.get_accuracy()
        }
        
    def _handle_control_action(self, action: str) -> Dict[str, Any]:
        """Handle control actions from web interface"""
        try:
            if action == 'start_logging':
                self.config['logging_enabled'] = True
                return {'status': 'success', 'message': 'Logging started'}
                
            elif action == 'stop_logging':
                self.config['logging_enabled'] = False
                return {'status': 'success', 'message': 'Logging stopped'}
                
            elif action == 'restart_gps':
                if self.gps_controller:
                    self.gps_controller.stop()
                    time.sleep(1)
                    self.gps_controller.start()
                return {'status': 'success', 'message': 'GPS restarted'}
                
            elif action == 'clear_position_history':
                self.position_history.clear()
                return {'status': 'success', 'message': 'Position history cleared'}
                
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}
                
        except Exception as e:
            self.logger.error(f"Control action error: {e}")
            return {'status': 'error', 'message': str(e)}
            
    def _save_config(self):
        """Save configuration to file"""
        try:
            config_file = Path(__file__).parent.parent / 'config' / 'web_config.json'
            config_file.parent.mkdir(exist_ok=True)
            
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            
    def _load_config(self):
        """Load configuration from file"""
        try:
            config_file = Path(__file__).parent.parent / 'config' / 'web_config.json'
            
            if config_file.exists():
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                    
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            
    def _update_loop(self):
        """Background thread for periodic updates"""
        while self.running:
            try:
                # Update position history
                if self.gps_controller:
                    position = self.gps_controller.get_position()
                    if position and position.valid:
                        position_data = position.to_dict()
                        position_data['timestamp'] = datetime.now().isoformat()
                        
                        self.position_history.append(position_data)
                        if len(self.position_history) > self.max_position_history:
                            self.position_history.pop(0)
                            
                # Update system stats history
                if self.system_monitor:
                    stats = self._get_system_status()
                    self.system_stats_history.append(stats)
                    if len(self.system_stats_history) > self.max_stats_history:
                        self.system_stats_history.pop(0)
                        
                # Broadcast updates to connected clients
                if self.connected_clients:
                    self.socketio.emit('status_update', self._get_system_status())
                    self.socketio.emit('gps_update', self._get_gps_data())
                    
                time.sleep(self.config['update_rate'])
                
            except Exception as e:
                self.logger.error(f"Update loop error: {e}")
                time.sleep(5)  # Wait before retrying
                
    def start(self):
        """Start the web server"""
        if self.running:
            return
            
        self.logger.info(f"Starting RTK Web Server on {self.host}:{self.port}")
        self.start_time = time.time()
        
        # Load configuration
        self._load_config()
        
        # Start update thread
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
        # Start Flask-SocketIO server
        if self.socketio:
            self.server_thread = threading.Thread(target=self.socketio.run, args=(self.app,), kwargs={'host': self.host, 'port': self.port, 'debug': False}, daemon=True)
            self.server_thread.start()
        else:
            self.logger.error("SocketIO not initialized. Cannot start server.")
        
    def stop(self):
        """Stop the web server"""
        if not self.running:
            return
            
        self.logger.info("Stopping RTK Web Server")
        self.running = False
        
        # Wait for update thread to finish
        if self.update_thread:
            self.update_thread.join(timeout=5)
            
        # Save configuration
        self._save_config()
        
    def set_gps_controller(self, gps_controller: LC29HController):
        """Set GPS controller reference"""
        self.gps_controller = gps_controller
        
    def set_system_monitor(self, system_monitor: SystemMonitor):
        """Set system monitor reference"""
        self.system_monitor = system_monitor
        
    def set_battery_monitor(self, battery_monitor: Any):
        """Set battery monitor reference"""
        self.battery_monitor = battery_monitor

# Standalone usage for development/testing
if __name__ == '__main__':
    # Initialize with mock components for testing
    from gnss.lc29h_controller import LC29HController
    from monitoring.system_monitor import SystemMonitor
    
    gps = LC29HController(simulate=True)
    system_mon = SystemMonitor()
    
    server = RTKWebServer(gps_controller=gps, system_monitor=system_mon)
    
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
