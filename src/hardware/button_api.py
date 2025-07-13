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
    
    def __init__(self, app_context=None, simulate_buttons: bool = False):
        """
        Initialize button API
        
        Args:
            app_context: Application context for button actions
            simulate_buttons: Use simulation mode
        """
        self.logger = logging.getLogger(__name__)
        self.app_context = app_context
        
        # Initialize button manager
        self.button_manager = ButtonManager(simulate_buttons=simulate_buttons)
        
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
    
    def simulate_button_press(self, button: ButtonType):
        """Simulate button press (for testing)"""
        self.button_manager.simulate_button_event(button, ButtonEvent.PRESS)
    
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
    
    def get_menu_selection(self, options: list, current_selection: int = 0) -> int:
        """
        Interactive menu selection using joystick
        
        Args:
            options: List of menu options
            current_selection: Currently selected option index
            
        Returns:
            Selected option index
        """
        selection = current_selection
        
        while True:
            events = self.get_pending_events()
            for event in events:
                if event['event'] == ButtonEvent.PRESS:
                    button = event['button']
                    
                    if button == ButtonType.JOY_UP:
                        selection = (selection - 1) % len(options)
                        self.logger.info(f"Menu selection: {options[selection]}")
                        
                    elif button == ButtonType.JOY_DOWN:
                        selection = (selection + 1) % len(options)
                        self.logger.info(f"Menu selection: {options[selection]}")
                        
                    elif button == ButtonType.JOY_PRESS or button == ButtonType.KEY3:
                        self.logger.info(f"Menu confirmed: {options[selection]}")
                        return selection
                        
                    elif button == ButtonType.KEY1:
                        # Cancel/back
                        self.logger.info("Menu cancelled")
                        return -1
            
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
def create_button_api(app_context=None, simulate: bool = False) -> ButtonAPI:
    """Create and start button API"""
    api = ButtonAPI(app_context, simulate_buttons=simulate)
    api.start()
    return api


def wait_for_any_button(timeout: Optional[float] = None) -> Optional[ButtonType]:
    """Quick function to wait for any button press"""
    api = ButtonAPI(simulate_buttons=True)
    api.start()
    try:
        return api.wait_for_button_press(timeout)
    finally:
        api.stop()


def get_user_choice(options: list, prompt: str = "Select option:") -> int:
    """Quick function to get user menu choice"""
    api = ButtonAPI(simulate_buttons=True)
    api.start()
    try:
        print(f"{prompt}")
        for i, option in enumerate(options):
            print(f"{i}: {option}")
        return api.get_menu_selection(options)
    finally:
        api.stop()


# Test function
if __name__ == "__main__":
    import time
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Button API...")
    
    # Test basic functionality
    api = ButtonAPI(simulate_buttons=True)
    api.start()
    
    print("Testing automatic button simulation...")
    print("Watch for button events...")
    
    try:
        # Monitor for 10 seconds
        for i in range(100):
            events = api.get_pending_events()
            for event in events:
                print(f"Event: {event['button'].value} {event['event'].value}")
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        pass
    finally:
        api.stop()
    
    print("Button API test complete!")
