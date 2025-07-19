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

from flask import Flask, render_template, request, jsonify, Response

# Import RTK Surveyor modules
from common.lc29h_controller import LC29HController, GNSSPosition, FixType
from hardware.system_monitor import SystemMonitor

# Optional imports
try:
    from flask_socketio import SocketIO, emit
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    
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
        
        # Initialize SocketIO with error handling
        self.socketio = None
        if SOCKETIO_AVAILABLE:
            try:
                self.socketio = SocketIO(self.app, cors_allowed_origins="*", logger=False, engineio_logger=False)
                self.logger.info("SocketIO initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize SocketIO: {e}")
                self.socketio = None
        else:
            self.logger.warning("SocketIO not available, using polling fallback")
        
        # Server state
        self.running = False
        self.startup_successful = False
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
        if self.socketio:
            self._setup_socketio_events()
        
    def _setup_routes(self):
        """Setup Flask routes with fallback for missing templates"""
        
        @self.app.route('/')
        def index():
            """Main dashboard page"""
            try:
                return render_template('dashboard.html')
            except:
                # Fallback if template is missing
                return self._create_simple_dashboard()
            
        @self.app.route('/config')
        def config_page():
            """Configuration management page"""
            try:
                return render_template('config.html')
            except:
                return self._create_simple_config()
            
        @self.app.route('/data')
        def data_page():
            """Data visualization page"""
            try:
                return render_template('data.html')
            except:
                return self._create_simple_data()
            
        @self.app.route('/logs')
        def logs_page():
            """System logs page"""
            try:
                return render_template('logs.html')
            except:
                return self._create_simple_logs()
            
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
    
    def _create_simple_dashboard(self):
        """Create a simple HTML dashboard when template is missing"""
        status = self._get_system_status()
        gps_data = self._get_gps_data()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Pi RTK Surveyor - Base Station</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .card {{ background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .status {{ display: flex; justify-content: space-between; }}
                .green {{ color: #28a745; }}
                .red {{ color: #dc3545; }}
                .yellow {{ color: #ffc107; }}
                h1 {{ color: #333; text-align: center; }}
                h2 {{ color: #555; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
                .refresh {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }}
            </style>
            <script>
                setTimeout(function(){{ window.location.reload(); }}, 5000);
            </script>
        </head>
        <body>
            <div class="container">
                <h1>🛰️ Pi RTK Surveyor - Base Station</h1>
                
                <div class="card">
                    <h2>System Status</h2>
                    <div class="status">
                        <span>Device Mode:</span>
                        <span class="green">{status.get('device_mode', 'Unknown')}</span>
                    </div>
                    <div class="status">
                        <span>RTK Enabled:</span>
                        <span class="{'green' if status.get('rtk_enabled') else 'red'}">{status.get('rtk_enabled', False)}</span>
                    </div>
                    <div class="status">
                        <span>CPU Temperature:</span>
                        <span>{status.get('cpu_temp', 0):.1f}°C</span>
                    </div>
                    <div class="status">
                        <span>Memory Usage:</span>
                        <span>{status.get('memory_usage', 0):.1f}%</span>
                    </div>
                    <div class="status">
                        <span>Connected Clients:</span>
                        <span>{status.get('connected_clients', 0)}</span>
                    </div>
                </div>
                
                <div class="card">
                    <h2>GPS Status</h2>
                    <div class="status">
                        <span>Connection:</span>
                        <span class="{'green' if gps_data.get('connected') else 'red'}">{gps_data.get('connected', 'Unknown')}</span>
                    </div>
                    <div class="status">
                        <span>RTK Fixed:</span>
                        <span class="{'green' if gps_data.get('rtk_fixed') else 'yellow'}">{gps_data.get('rtk_fixed', False)}</span>
                    </div>
                    <div class="status">
                        <span>RTK Float:</span>
                        <span class="{'yellow' if gps_data.get('rtk_float') else 'red'}">{gps_data.get('rtk_float', False)}</span>
                    </div>
                </div>
                
                <div class="card">
                    <h2>API Endpoints</h2>
                    <p><a href="/api/status">/api/status</a> - System status JSON</p>
                    <p><a href="/api/gps">/api/gps</a> - GPS data JSON</p>
                    <p><a href="/api/position-history">/api/position-history</a> - Position history</p>
                    <p><a href="/api/system-stats">/api/system-stats</a> - System statistics</p>
                </div>
                
                <div style="text-align: center; margin: 20px 0;">
                    <button class="refresh" onclick="window.location.reload()">🔄 Refresh</button>
                </div>
                
                <div style="text-align: center; color: #666; font-size: 12px;">
                    Auto-refresh every 5 seconds | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def _create_simple_config(self):
        """Create a simple configuration page"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Configuration - Pi RTK Surveyor</title></head>
        <body style="font-family: Arial; margin: 20px;">
            <h1>Configuration</h1>
            <p>Current configuration:</p>
            <pre>{json.dumps(self.config, indent=2)}</pre>
            <p><a href="/">← Back to Dashboard</a></p>
        </body>
        </html>
        """
    
    def _create_simple_data(self):
        """Create a simple data page"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Data - Pi RTK Surveyor</title></head>
        <body style="font-family: Arial; margin: 20px;">
            <h1>Data Visualization</h1>
            <p>Position history: {len(self.position_history)} points</p>
            <p>System stats: {len(self.system_stats_history)} entries</p>
            <p><a href="/">← Back to Dashboard</a></p>
        </body>
        </html>
        """
    
    def _create_simple_logs(self):
        """Create a simple logs page"""
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Logs - Pi RTK Surveyor</title></head>
        <body style="font-family: Arial; margin: 20px;">
            <h1>System Logs</h1>
            <p>Check system logs with: <code>journalctl -u pi-rtk-surveyor</code></p>
            <p><a href="/">← Back to Dashboard</a></p>
        </body>
        </html>
        """
            
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
                    if self.socketio:
                        self.socketio.emit('status_update', self._get_system_status())
                        self.socketio.emit('gps_update', self._get_gps_data())
                    else:
                        # Fallback for polling if SocketIO is not available
                        self.logger.warning("SocketIO not available, broadcasting updates via polling.")
                        # This part would require a polling mechanism if SocketIO is off
                        # For now, we'll just log a warning.
                        pass
                    
                time.sleep(self.config['update_rate'])
                
            except Exception as e:
                self.logger.error(f"Update loop error: {e}")
                time.sleep(5)  # Wait before retrying
                
    def start(self):
        """Start the web server with robust error handling"""
        if self.running:
            return
            
        self.logger.info(f"Starting RTK Web Server on {self.host}:{self.port}")
        self.start_time = time.time()
        
        try:
            # Load configuration
            self._load_config()
            
            # Start update thread
            self.running = True
            if self.socketio:
                self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
                self.update_thread.start()
            
            # Start Flask server in background with timeout
            self.server_thread = threading.Thread(target=self._start_server, daemon=True)
            self.server_thread.start()
            
            # Wait for server to start (with timeout)
            timeout = 5.0  # 5 second timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.startup_successful:
                    self.logger.info("Web server started successfully")
                    return
                time.sleep(0.1)
            
            # If we get here, startup may have failed
            self.logger.warning("Web server startup timeout - continuing anyway")
            self.startup_successful = True  # Assume it's working
            
        except Exception as e:
            self.logger.error(f"Failed to start web server: {e}")
            self.startup_successful = False
    
    def _start_server(self):
        """Start the actual Flask/SocketIO server"""
        try:
            if self.socketio:
                self.logger.info("Starting SocketIO server...")
                self.startup_successful = True  # Set flag before starting
                self.socketio.run(self.app, host=self.host, port=self.port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
            else:
                self.logger.info("Starting basic Flask server...")
                self.startup_successful = True  # Set flag before starting  
                self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
        except Exception as e:
            self.logger.error(f"Server startup failed: {e}")
            self.startup_successful = False
        
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
