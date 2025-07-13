/**
 * Pi RTK Surveyor Dashboard JavaScript
 * Handles charts, control buttons, and dashboard-specific functionality
 */

class RTKDashboard {
    constructor() {
        this.positionChart = null;
        this.systemChart = null;
        this.chartUpdateInterval = null;
        this.maxDataPoints = 50;
        
        this.init();
    }
    
    init() {
        this.setupCharts();
        this.setupControlButtons();
        this.startChartUpdates();
        
        // Listen for data updates from main app
        if (window.rtkApp) {
            // Hook into the main app's data update events
            const originalHandleGPSUpdate = window.rtkApp.handleGPSUpdate;
            window.rtkApp.handleGPSUpdate = (data) => {
                originalHandleGPSUpdate.call(window.rtkApp, data);
                this.updatePositionChart(data);
            };
            
            const originalHandleStatusUpdate = window.rtkApp.handleStatusUpdate;
            window.rtkApp.handleStatusUpdate = (data) => {
                originalHandleStatusUpdate.call(window.rtkApp, data);
                this.updateSystemChart(data);
            };
        }
    }
    
    setupCharts() {
        this.setupPositionChart();
        this.setupSystemChart();
    }
    
    setupPositionChart() {
        const ctx = document.getElementById('positionChart');
        if (!ctx) return;
        
        this.positionChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Latitude',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Longitude',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.1,
                        yAxisID: 'y1'
                    },
                    {
                        label: 'Elevation (m)',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        tension: 0.1,
                        yAxisID: 'y2'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Latitude'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Longitude'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    },
                    y2: {
                        type: 'linear',
                        display: false,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Elevation (m)'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'GPS Position History'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
    }
    
    setupSystemChart() {
        const ctx = document.getElementById('systemChart');
        if (!ctx) return;
        
        this.systemChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'CPU Temperature (°C)',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'CPU Usage (%)',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        tension: 0.1,
                        yAxisID: 'y1'
                    },
                    {
                        label: 'Memory Usage (%)',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1,
                        yAxisID: 'y1'
                    },
                    {
                        label: 'Battery Level (%)',
                        data: [],
                        borderColor: 'rgb(255, 205, 86)',
                        backgroundColor: 'rgba(255, 205, 86, 0.2)',
                        tension: 0.1,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Temperature (°C)'
                        },
                        min: 0,
                        max: 100,
                        grid: {
                            drawOnChartArea: false,
                        },
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Percentage (%)'
                        },
                        min: 0,
                        max: 100,
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'System Statistics'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
    }
    
    setupControlButtons() {
        // Start/Stop Logging buttons
        const startLoggingBtn = document.getElementById('start-logging-btn');
        const stopLoggingBtn = document.getElementById('stop-logging-btn');
        
        if (startLoggingBtn) {
            startLoggingBtn.addEventListener('click', () => {
                this.handleControlAction('start_logging');
            });
        }
        
        if (stopLoggingBtn) {
            stopLoggingBtn.addEventListener('click', () => {
                this.handleControlAction('stop_logging');
            });
        }
        
        // Restart GPS button
        const restartGpsBtn = document.getElementById('restart-gps-btn');
        if (restartGpsBtn) {
            restartGpsBtn.addEventListener('click', () => {
                this.handleControlAction('restart_gps');
            });
        }
        
        // Clear History button
        const clearHistoryBtn = document.getElementById('clear-history-btn');
        if (clearHistoryBtn) {
            clearHistoryBtn.addEventListener('click', () => {
                this.handleControlAction('clear_position_history');
            });
        }
    }
    
    async handleControlAction(action) {
        if (!window.rtkApp) return;
        
        const result = await window.rtkApp.postControlAction(action);
        
        // Update UI based on action
        if (result.status === 'success') {
            this.updateControlButtonStates(action);
            
            // Special handling for clear history
            if (action === 'clear_position_history') {
                this.clearPositionChart();
            }
        }
    }
    
    updateControlButtonStates(action) {
        const startLoggingBtn = document.getElementById('start-logging-btn');
        const stopLoggingBtn = document.getElementById('stop-logging-btn');
        const loggingStatus = document.getElementById('logging-status');
        
        if (action === 'start_logging') {
            if (startLoggingBtn) startLoggingBtn.style.display = 'none';
            if (stopLoggingBtn) stopLoggingBtn.style.display = 'block';
            if (loggingStatus) {
                loggingStatus.textContent = 'Active';
                loggingStatus.className = 'badge bg-success';
            }
        } else if (action === 'stop_logging') {
            if (startLoggingBtn) startLoggingBtn.style.display = 'block';
            if (stopLoggingBtn) stopLoggingBtn.style.display = 'none';
            if (loggingStatus) {
                loggingStatus.textContent = 'Stopped';
                loggingStatus.className = 'badge bg-secondary';
            }
        }
    }
    
    updatePositionChart(gpsData) {
        if (!this.positionChart || !gpsData || !gpsData.position || !gpsData.position.valid) {
            return;
        }
        
        const now = new Date();
        const timeLabel = now.toLocaleTimeString();
        const position = gpsData.position;
        
        // Add new data point
        this.positionChart.data.labels.push(timeLabel);
        this.positionChart.data.datasets[0].data.push(position.latitude);
        this.positionChart.data.datasets[1].data.push(position.longitude);
        this.positionChart.data.datasets[2].data.push(position.elevation);
        
        // Remove old data points if we have too many
        if (this.positionChart.data.labels.length > this.maxDataPoints) {
            this.positionChart.data.labels.shift();
            this.positionChart.data.datasets.forEach(dataset => {
                dataset.data.shift();
            });
        }
        
        // Update chart color based on RTK status
        if (gpsData.rtk_fixed) {
            this.positionChart.data.datasets[0].borderColor = 'rgb(40, 167, 69)';
            this.positionChart.data.datasets[1].borderColor = 'rgb(40, 167, 69)';
            this.positionChart.data.datasets[2].borderColor = 'rgb(40, 167, 69)';
        } else if (gpsData.rtk_float) {
            this.positionChart.data.datasets[0].borderColor = 'rgb(255, 193, 7)';
            this.positionChart.data.datasets[1].borderColor = 'rgb(255, 193, 7)';
            this.positionChart.data.datasets[2].borderColor = 'rgb(255, 193, 7)';
        } else {
            this.positionChart.data.datasets[0].borderColor = 'rgb(75, 192, 192)';
            this.positionChart.data.datasets[1].borderColor = 'rgb(255, 99, 132)';
            this.positionChart.data.datasets[2].borderColor = 'rgb(54, 162, 235)';
        }
        
        this.positionChart.update('none');
    }
    
    updateSystemChart(systemData) {
        if (!this.systemChart || !systemData) {
            return;
        }
        
        const now = new Date();
        const timeLabel = now.toLocaleTimeString();
        
        // Add new data point
        this.systemChart.data.labels.push(timeLabel);
        this.systemChart.data.datasets[0].data.push(systemData.cpu_temp || 0);
        this.systemChart.data.datasets[1].data.push(systemData.cpu_usage || 0);
        this.systemChart.data.datasets[2].data.push(systemData.memory_usage || 0);
        this.systemChart.data.datasets[3].data.push(systemData.battery_level || 0);
        
        // Remove old data points if we have too many
        if (this.systemChart.data.labels.length > this.maxDataPoints) {
            this.systemChart.data.labels.shift();
            this.systemChart.data.datasets.forEach(dataset => {
                dataset.data.shift();
            });
        }
        
        this.systemChart.update('none');
    }
    
    clearPositionChart() {
        if (this.positionChart) {
            this.positionChart.data.labels = [];
            this.positionChart.data.datasets.forEach(dataset => {
                dataset.data = [];
            });
            this.positionChart.update();
        }
    }
    
    clearSystemChart() {
        if (this.systemChart) {
            this.systemChart.data.labels = [];
            this.systemChart.data.datasets.forEach(dataset => {
                dataset.data = [];
            });
            this.systemChart.update();
        }
    }
    
    startChartUpdates() {
        // Periodic chart updates from API
        this.chartUpdateInterval = setInterval(async () => {
            try {
                if (window.rtkApp && window.rtkApp.connected) {
                    // Get position history
                    const positionHistory = await window.rtkApp.apiCall('/api/position-history');
                    this.updatePositionChartFromHistory(positionHistory);
                    
                    // Get system stats
                    const systemStats = await window.rtkApp.apiCall('/api/system-stats');
                    this.updateSystemChartFromHistory(systemStats);
                }
            } catch (error) {
                console.error('Failed to update charts from API:', error);
            }
        }, 30000); // Update every 30 seconds
    }
    
    updatePositionChartFromHistory(history) {
        if (!this.positionChart || !history || !Array.isArray(history)) {
            return;
        }
        
        // Clear existing data
        this.positionChart.data.labels = [];
        this.positionChart.data.datasets.forEach(dataset => {
            dataset.data = [];
        });
        
        // Add historical data
        history.slice(-this.maxDataPoints).forEach(point => {
            const time = new Date(point.timestamp).toLocaleTimeString();
            this.positionChart.data.labels.push(time);
            this.positionChart.data.datasets[0].data.push(point.latitude);
            this.positionChart.data.datasets[1].data.push(point.longitude);
            this.positionChart.data.datasets[2].data.push(point.elevation);
        });
        
        this.positionChart.update();
    }
    
    updateSystemChartFromHistory(history) {
        if (!this.systemChart || !history || !Array.isArray(history)) {
            return;
        }
        
        // Clear existing data
        this.systemChart.data.labels = [];
        this.systemChart.data.datasets.forEach(dataset => {
            dataset.data = [];
        });
        
        // Add historical data
        history.slice(-this.maxDataPoints).forEach(point => {
            const time = new Date(point.timestamp).toLocaleTimeString();
            this.systemChart.data.labels.push(time);
            this.systemChart.data.datasets[0].data.push(point.cpu_temp || 0);
            this.systemChart.data.datasets[1].data.push(point.cpu_usage || 0);
            this.systemChart.data.datasets[2].data.push(point.memory_usage || 0);
            this.systemChart.data.datasets[3].data.push(point.battery_level || 0);
        });
        
        this.systemChart.update();
    }
    
    exportChartData() {
        const data = {
            position_history: this.positionChart ? {
                labels: this.positionChart.data.labels,
                datasets: this.positionChart.data.datasets.map(dataset => ({
                    label: dataset.label,
                    data: dataset.data
                }))
            } : null,
            system_stats: this.systemChart ? {
                labels: this.systemChart.data.labels,
                datasets: this.systemChart.data.datasets.map(dataset => ({
                    label: dataset.label,
                    data: dataset.data
                }))
            } : null,
            timestamp: new Date().toISOString()
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `rtk-dashboard-data-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    destroy() {
        if (this.chartUpdateInterval) {
            clearInterval(this.chartUpdateInterval);
        }
        
        if (this.positionChart) {
            this.positionChart.destroy();
        }
        
        if (this.systemChart) {
            this.systemChart.destroy();
        }
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait for the main app to be ready
    const initDashboard = () => {
        if (window.rtkApp) {
            window.rtkDashboard = new RTKDashboard();
        } else {
            setTimeout(initDashboard, 100);
        }
    };
    
    initDashboard();
});

// Export for use in other modules
window.RTKDashboard = RTKDashboard; 