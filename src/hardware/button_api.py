#!/usr/bin/env python3
"""
Button API for Pi RTK Surveyor
Simplified interface for button interactions
"""

import logging
from typing import Callable, Optional
from .button_manager import ButtonManager, ButtonType, ButtonEvent, ButtonActions


class ButtonAPI:
    """Simplified button interface for application modules"""
    
    def __init__(self, app_context=None):
        """
        Initialize button API
        
        Args:
            app_context: Application context for button actions
        """
        self.logger = logging.getLogger(__name__)
        self.app_context = app_context
        
        # Initialize button manager
        self.button_manager = ButtonManager()
        
        # Initialize button actions
        if app_context:
            self.button_actions = ButtonActions(app_context)
            self._register_default_actions()
        
        # Application state
        self.current_mode = "menu"  # menu, base, rover, system
        self.menu_position = 0
        
    def start(self):
        """Start button monitoring"""
        self.button_manager.start()
        self.logger.info("Button API started")
        
    def stop(self):
        """Stop button monitoring"""
        self.button_manager.stop()
        self.logger.info("Button API stopped")
    
    def _register_default_actions(self):
        """Register default button action handlers"""
        # KEY1 - Mode/Menu cycling
        self.button_manager.register_callback(
            ButtonType.KEY1, ButtonEvent.PRESS, 
            self.button_actions.handle_key1_press
        )
        
        # KEY2 - Settings/Brightness
        self.button_manager.register_callback(
            ButtonType.KEY2, ButtonEvent.PRESS,
            self.button_actions.handle_key2_press
        )
        
        # KEY3 - Action/Logging
        self.button_manager.register_callback(
            ButtonType.KEY3, ButtonEvent.PRESS,
            self.button_actions.handle_key3_press
        )
        
        # Joystick navigation
        for joy_button in [ButtonType.JOY_UP, ButtonType.JOY_DOWN, 
                          ButtonType.JOY_LEFT, ButtonType.JOY_RIGHT, ButtonType.JOY_PRESS]:
            self.button_manager.register_callback(
                joy_button, ButtonEvent.PRESS,
                self.button_actions.handle_joystick_navigation
            )
    
    def register_custom_handler(self, button: ButtonType, event: ButtonEvent, handler: Callable):
        """Register custom button handler"""
        self.button_manager.register_callback(button, event, handler)
        
    def unregister_handler(self, button: ButtonType, event: ButtonEvent, handler: Callable):
        """Unregister button handler"""
        self.button_manager.unregister_callback(button, event, handler)
    
    def get_pending_events(self):
        """Get pending button events"""
        return self.button_manager.get_button_events()
    
    def is_button_pressed(self, button: ButtonType) -> bool:
        """Check if button is currently pressed"""
        return self.button_manager.is_button_pressed(button)
    
    # Convenience methods for common operations
    def wait_for_button_press(self, timeout: Optional[float] = None) -> Optional[ButtonType]:
        """
        Wait for any button press
        
        Args:
            timeout: Maximum time to wait (None for infinite)
            
        Returns:
            ButtonType that was pressed, or None if timeout
        """
        import time
        start_time = time.time()
        
        while True:
            events = self.get_pending_events()
            for event in events:
                if event['event'] == ButtonEvent.PRESS:
                    return event['button']
            
            if timeout and (time.time() - start_time) > timeout:
                return None
                
            time.sleep(0.01)  # Small delay to prevent busy waiting
    
    def wait_for_specific_button(self, button: ButtonType, timeout: Optional[float] = None) -> bool:
        """
        Wait for specific button press
        
        Args:
            button: Button to wait for
            timeout: Maximum time to wait
            
        Returns:
            True if button was pressed, False if timeout
        """
        import time
        start_time = time.time()
        
        while True:
            events = self.get_pending_events()
            for event in events:
                if (event['event'] == ButtonEvent.PRESS and 
                    event['button'] == button):
                    return True
            
            if timeout and (time.time() - start_time) > timeout:
                return False
                
            time.sleep(0.01)
    
    def confirm_action(self, message: str, timeout: float = 10.0) -> bool:
        """
        Confirm action with user
        
        Args:
            message: Confirmation message
            timeout: Timeout in seconds
            
        Returns:
            True if confirmed, False if cancelled or timeout
        """
        import time
        
        self.logger.info(f"Confirmation required: {message}")
        self.logger.info("Press KEY3 to confirm, KEY1 to cancel")
        
        start_time = time.time()
        
        while True:
            events = self.get_pending_events()
            for event in events:
                if event['event'] == ButtonEvent.PRESS:
                    if event['button'] == ButtonType.KEY3:
                        self.logger.info("Action confirmed")
                        return True
                    elif event['button'] == ButtonType.KEY1:
                        self.logger.info("Action cancelled")
                        return False
            
            if (time.time() - start_time) > timeout:
                self.logger.info("Confirmation timeout")
                return False
                
            time.sleep(0.01)


# Convenience functions for quick button operations
def create_button_api(app_context=None) -> ButtonAPI:
    """Create and start button API"""
    api = ButtonAPI(app_context)
    api.start()
    return api
