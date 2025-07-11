/**
 * Pi RTK Surveyor Web Interface - Main JavaScript
 * Handles Socket.IO connections, real-time updates, and general functionality
 */

class RTKWebApp {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.lastUpdateTime = 0;
        this.connectionRetryCount = 0;
        this.maxRetries = 5;
        this.retryDelay = 2000;
        
        // Data storage
        this.gpsData = null;
        this.systemStatus = null;
        this.positionHistory = [];
        this.systemStats = [];
        
        // UI elements
        this.elements = {
            connectionStatus: document.getElementById('connection-status'),
            connectionText: document.getElementById('connection-text'),
            systemTime: document.getElementById('system-time'),
            uptime: document.getElementById('uptime')
        };
        
        this.init();
    }
    
    init() {
        this.setupSocketConnection();
        this.setupUI();
        this.startUpdateLoop();
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseUpdates();
            } else {
                this.resumeUpdates();
            }
        });
        
        // Handle network status changes
        window.addEventListener('online', () => this.handleNetworkOnline());
        window.addEventListener('offline', () => this.handleNetworkOffline());
    }
    
    setupSocketConnection() {
        try {
            this.socket = io({
                autoConnect: true,
                reconnection: true,
                reconnectionDelay: this.retryDelay,
                reconnectionAttempts: this.maxRetries,
                timeout: 10000
            });
            
            this.socket.on('connect', () => this.handleConnect());
            this.socket.on('disconnect', () => this.handleDisconnect());
            this.socket.on('connect_error', (error) => this.handleConnectionError(error));
            this.socket.on('status_update', (data) => this.handleStatusUpdate(data));
            this.socket.on('gps_update', (data) => this.handleGPSUpdate(data));
            
        } catch (error) {
            console.error('Failed to initialize Socket.IO:', error);
            this.handleConnectionError(error);
        }
    }
    
    setupUI() {
        // Update system time every second
        setInterval(() => {
            this.updateSystemTime();
        }, 1000);
        
        // Setup tooltips
        this.setupTooltips();
        
        // Setup keyboard shortcuts
        this.setupKeyboardShortcuts();
    }
    
    setupTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(tooltipTriggerEl => {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            // Ctrl+R: Refresh data
            if (event.ctrlKey && event.key === 'r') {
                event.preventDefault();
                this.refreshData();
            }
            
            // Ctrl+D: Toggle debug mode
            if (event.ctrlKey && event.key === 'd') {
                event.preventDefault();
                this.toggleDebugMode();
            }
        });
    }
    
    handleConnect() {
        console.log('Connected to RTK server');
        this.connected = true;
        this.connectionRetryCount = 0;
        this.updateConnectionStatus('Connected', 'success');
        this.requestInitialData();
    }
    
    handleDisconnect() {
        console.log('Disconnected from RTK server');
        this.connected = false;
        this.updateConnectionStatus('Disconnected', 'danger');
    }
    
    handleConnectionError(error) {
        console.error('Connection error:', error);
        this.connected = false;
        this.connectionRetryCount++;
        
        if (this.connectionRetryCount >= this.maxRetries) {
            this.updateConnectionStatus('Connection Failed', 'danger');
        } else {
            this.updateConnectionStatus(`Reconnecting... (${this.connectionRetryCount}/${this.maxRetries})`, 'warning');
        }
    }
    
    handleStatusUpdate(data) {
        this.systemStatus = data;
        this.updateSystemStatusDisplay();
        this.lastUpdateTime = Date.now();
    }
    
    handleGPSUpdate(data) {
        this.gpsData = data;
        this.updateGPSStatusDisplay();
        this.lastUpdateTime = Date.now();
    }
    
    updateConnectionStatus(text, type) {
        if (this.elements.connectionStatus) {
            this.elements.connectionStatus.className = `fas fa-circle text-${type}`;
        }
        
        if (this.elements.connectionText) {
            this.elements.connectionText.textContent = text;
        }
    }
    
    updateSystemTime() {
        if (this.elements.systemTime) {
            const now = new Date();
            this.elements.systemTime.textContent = now.toLocaleTimeString();
        }
    }
    
    updateSystemStatusDisplay() {
        if (!this.systemStatus) return;
        
        // Update uptime
        if (this.elements.uptime && this.systemStatus.uptime) {
            const uptimeSeconds = Math.floor(this.systemStatus.uptime);
            const hours = Math.floor(uptimeSeconds / 3600);
            const minutes = Math.floor((uptimeSeconds % 3600) / 60);
            const seconds = uptimeSeconds % 60;
            this.elements.uptime.textContent = `Uptime: ${hours}h ${minutes}m ${seconds}s`;
        }
        
        // Update individual status elements
        this.updateElement('cpu-temp', this.systemStatus.cpu_temp ? `${this.systemStatus.cpu_temp.toFixed(1)}°C` : '--');
        this.updateElement('cpu-usage', this.systemStatus.cpu_usage ? `${this.systemStatus.cpu_usage.toFixed(1)}%` : '--');
        this.updateElement('memory-percent', this.systemStatus.memory_usage ? `${this.systemStatus.memory_usage.toFixed(1)}%` : '--');
        this.updateElement('disk-percent', this.systemStatus.disk_usage ? `${this.systemStatus.disk_usage.toFixed(1)}%` : '--');
        
        // Update progress bars
        this.updateProgressBar('memory-bar', this.systemStatus.memory_usage);
        this.updateProgressBar('disk-bar', this.systemStatus.disk_usage);
        
        // Update battery status
        this.updateElement('battery-level', this.systemStatus.battery_level ? `${this.systemStatus.battery_level}%` : '--');
        this.updateElement('battery-runtime', this.systemStatus.estimated_runtime ? 
            this.formatRuntime(this.systemStatus.estimated_runtime) : '--');
        
        // Update device status
        this.updateElement('device-mode', this.systemStatus.device_mode || 'Unknown');
        this.updateElement('rtk-enabled', this.systemStatus.rtk_enabled ? 'Yes' : 'No');
        this.updateElement('logging-status', this.systemStatus.logging_enabled ? 'Active' : 'Stopped');
        this.updateElement('connected-clients', this.systemStatus.connected_clients || '--');
    }
    
    updateGPSStatusDisplay() {
        if (!this.gpsData) return;
        
        // Update GPS connection status
        const gpsStatusElement = document.getElementById('gps-status');
        if (gpsStatusElement) {
            if (this.gpsData.connected && this.gpsData.position && this.gpsData.position.valid) {
                if (this.gpsData.rtk_fixed) {
                    gpsStatusElement.innerHTML = '<i class="fas fa-satellite text-success"></i> RTK Fixed';
                    gpsStatusElement.className = 'h4 mb-0 text-success';
                } else if (this.gpsData.rtk_float) {
                    gpsStatusElement.innerHTML = '<i class="fas fa-satellite text-warning"></i> RTK Float';
                    gpsStatusElement.className = 'h4 mb-0 text-warning';
                } else {
                    gpsStatusElement.innerHTML = '<i class="fas fa-satellite text-info"></i> GPS Fix';
                    gpsStatusElement.className = 'h4 mb-0 text-info';
                }
            } else {
                gpsStatusElement.innerHTML = '<i class="fas fa-satellite text-danger"></i> No Fix';
                gpsStatusElement.className = 'h4 mb-0 text-danger';
            }
        }
        
        // Update position data
        if (this.gpsData.position) {
            const pos = this.gpsData.position;
            this.updateElement('latitude-value', pos.latitude ? pos.latitude.toFixed(8) : '--');
            this.updateElement('longitude-value', pos.longitude ? pos.longitude.toFixed(8) : '--');
            this.updateElement('elevation-value', pos.elevation ? `${pos.elevation.toFixed(2)}m` : '--');
            this.updateElement('satellites-count', pos.satellites_used || '--');
            this.updateElement('hdop-value', pos.hdop ? pos.hdop.toFixed(2) : '--');
            this.updateElement('vdop-value', pos.vdop ? pos.vdop.toFixed(2) : '--');
            this.updateElement('pdop-value', pos.pdop ? pos.pdop.toFixed(2) : '--');
        }
        
        // Update RTK status message
        this.updateRTKStatus();
    }
    
    updateRTKStatus() {
        const rtkStatusElement = document.getElementById('rtk-status');
        const rtkMessageElement = document.getElementById('rtk-message');
        
        if (rtkStatusElement && rtkMessageElement) {
            if (this.gpsData.rtk_fixed) {
                rtkStatusElement.className = 'alert alert-success mb-2';
                rtkMessageElement.textContent = 'RTK Fixed - Centimeter accuracy achieved';
                rtkStatusElement.style.display = 'block';
            } else if (this.gpsData.rtk_float) {
                rtkStatusElement.className = 'alert alert-warning mb-2';
                rtkMessageElement.textContent = 'RTK Float - Decimeter accuracy available';
                rtkStatusElement.style.display = 'block';
            } else if (this.gpsData.connected && this.gpsData.position && this.gpsData.position.valid) {
                rtkStatusElement.className = 'alert alert-info mb-2';
                rtkMessageElement.textContent = 'Standard GPS - Meter level accuracy';
                rtkStatusElement.style.display = 'block';
            } else {
                rtkStatusElement.style.display = 'none';
            }
        }
    }
    
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
    
    updateProgressBar(id, value) {
        const progressBar = document.getElementById(id);
        if (progressBar && value !== undefined) {
            progressBar.style.width = `${Math.min(100, Math.max(0, value))}%`;
            
            // Update color based on value
            progressBar.className = 'progress-bar';
            if (value > 90) {
                progressBar.classList.add('bg-danger');
            } else if (value > 75) {
                progressBar.classList.add('bg-warning');
            } else {
                progressBar.classList.add('bg-success');
            }
        }
    }
    
    formatRuntime(seconds) {
        if (!seconds || seconds <= 0) return '--';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }
    
    requestInitialData() {
        if (this.socket && this.connected) {
            this.socket.emit('request_update');
        }
    }
    
    refreshData() {
        if (this.socket && this.connected) {
            this.socket.emit('request_update');
            this.showNotification('Data refreshed', 'success');
        } else {
            this.showNotification('Not connected to server', 'warning');
        }
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            <strong>${type.charAt(0).toUpperCase() + type.slice(1)}:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
    
    toggleDebugMode() {
        const debugMode = localStorage.getItem('rtk-debug-mode') === 'true';
        localStorage.setItem('rtk-debug-mode', !debugMode);
        
        if (!debugMode) {
            this.showNotification('Debug mode enabled', 'info');
            this.enableDebugMode();
        } else {
            this.showNotification('Debug mode disabled', 'info');
            this.disableDebugMode();
        }
    }
    
    enableDebugMode() {
        document.body.classList.add('debug-mode');
        
        // Add debug info to page
        const debugInfo = document.createElement('div');
        debugInfo.id = 'debug-info';
        debugInfo.className = 'position-fixed bottom-0 start-0 bg-dark text-white p-2 m-2 rounded';
        debugInfo.style.cssText = 'z-index: 9999; font-family: monospace; font-size: 0.8rem;';
        debugInfo.innerHTML = `
            <div>Debug Mode Active</div>
            <div id="debug-connection">Connection: ${this.connected ? 'Connected' : 'Disconnected'}</div>
            <div id="debug-last-update">Last Update: ${new Date(this.lastUpdateTime).toLocaleTimeString()}</div>
        `;
        
        document.body.appendChild(debugInfo);
        
        // Update debug info regularly
        this.debugUpdateInterval = setInterval(() => {
            this.updateDebugInfo();
        }, 1000);
    }
    
    disableDebugMode() {
        document.body.classList.remove('debug-mode');
        
        const debugInfo = document.getElementById('debug-info');
        if (debugInfo) {
            debugInfo.remove();
        }
        
        if (this.debugUpdateInterval) {
            clearInterval(this.debugUpdateInterval);
            this.debugUpdateInterval = null;
        }
    }
    
    updateDebugInfo() {
        const connectionDebug = document.getElementById('debug-connection');
        const lastUpdateDebug = document.getElementById('debug-last-update');
        
        if (connectionDebug) {
            connectionDebug.textContent = `Connection: ${this.connected ? 'Connected' : 'Disconnected'}`;
        }
        
        if (lastUpdateDebug) {
            lastUpdateDebug.textContent = `Last Update: ${new Date(this.lastUpdateTime).toLocaleTimeString()}`;
        }
    }
    
    handleNetworkOnline() {
        this.showNotification('Network connection restored', 'success');
        if (this.socket && !this.connected) {
            this.socket.connect();
        }
    }
    
    handleNetworkOffline() {
        this.showNotification('Network connection lost', 'warning');
        this.connected = false;
        this.updateConnectionStatus('Offline', 'danger');
    }
    
    pauseUpdates() {
        if (this.socket) {
            this.socket.disconnect();
        }
    }
    
    resumeUpdates() {
        if (this.socket) {
            this.socket.connect();
        }
    }
    
    startUpdateLoop() {
        // Main update loop - runs every 5 seconds
        setInterval(() => {
            // Check if we haven't received an update in a while
            if (this.connected && Date.now() - this.lastUpdateTime > 10000) {
                this.showNotification('No recent updates from server', 'warning');
            }
        }, 5000);
    }
    
    // API helper methods
    async apiCall(endpoint, options = {}) {
        try {
            const response = await fetch(endpoint, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            this.showNotification(`API Error: ${error.message}`, 'danger');
            throw error;
        }
    }
    
    async postControlAction(action) {
        try {
            const result = await this.apiCall(`/api/control/${action}`, {
                method: 'POST'
            });
            
            if (result.status === 'success') {
                this.showNotification(result.message, 'success');
            } else {
                this.showNotification(result.message, 'danger');
            }
            
            return result;
        } catch (error) {
            return { status: 'error', message: error.message };
        }
    }
}

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.rtkApp = new RTKWebApp();
    
    // Initialize debug mode if enabled
    if (localStorage.getItem('rtk-debug-mode') === 'true') {
        window.rtkApp.enableDebugMode();
    }
});

// Export for use in other modules
window.RTKWebApp = RTKWebApp; 