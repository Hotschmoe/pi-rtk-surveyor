#!/usr/bin/env python3
"""
Web Server Launcher for Pi RTK Surveyor
This script properly launches the web server with correct imports
"""

import os
import sys
from pathlib import Path

# Add software directory to Python path
project_dir = Path(__file__).parent
software_dir = project_dir / 'software'
sys.path.insert(0, str(software_dir))

# Import and run the web server
from web.web_server import RTKWebServer
from gnss.lc29h_controller import LC29HController
from monitoring.system_monitor import SystemMonitor

def main():
    """Main entry point for web server"""
    print("Starting Pi RTK Surveyor Web Server...")
    print("Web interface will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop")
    
    # Initialize components
    gps = LC29HController(simulate=True)
    system_mon = SystemMonitor()
    
    server = RTKWebServer(gps_controller=gps, system_monitor=system_mon)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down web server...")
        server.stop()
        print("Web server stopped.")

if __name__ == '__main__':
    main() 