"""
Pi RTK Surveyor Web Interface Package
Provides Flask-based web interface for RTK base station monitoring
"""

from .web_server import RTKWebServer

__version__ = '1.0.0'
__author__ = 'Pi RTK Surveyor Project'

__all__ = ['RTKWebServer']
