#!/usr/bin/env python3
"""
Quick Integration Test for Pi RTK Surveyor
Tests button manager integration with main application
"""

import sys
import time
import logging
from pathlib import Path

# Add software directory to path
software_dir = Path(__file__).parent / "software"
sys.path.insert(0, str(software_dir))

def test_button_integration():
    """Test button manager integration"""
    print("🧪 Testing Pi RTK Surveyor Button Integration")
    print("=" * 50)
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        from main import RTKSurveyorApp
        
        print("✅ Successfully imported RTKSurveyorApp")
        
        # Create app in simulation mode
        app = RTKSurveyorApp(simulate_hardware=True)
        print("✅ Created RTKSurveyorApp instance")
        
        # Test initialization components
        print("\n🔧 Testing component initialization...")
        
        # Initialize OLED (simulation)
        from display.oled_manager import OLEDManager
        oled = OLEDManager(simulate_display=True)
        print("✅ OLED Manager initialization")
        
        # Initialize button API (simulation)
        from input.button_api import ButtonAPI
        button_api = ButtonAPI(app_context=app, simulate_buttons=True)
        print("✅ Button API initialization")
        
        # Test button events
        print("\n🎮 Testing button events...")
        button_api.start()
        
        # Simulate some button presses
        from input.button_manager import ButtonType
        button_api.simulate_button_press(ButtonType.KEY1)
        time.sleep(0.1)
        button_api.simulate_button_press(ButtonType.KEY2)
        time.sleep(0.1)
        button_api.simulate_button_press(ButtonType.KEY3)
        time.sleep(0.1)
        
        # Check for events
        events = button_api.get_pending_events()
        print(f"✅ Button events generated: {len(events)}")
        
        for event in events:
            print(f"   - {event['button'].value}: {event['event'].value}")
        
        button_api.stop()
        
        # Test app methods
        print("\n⚙️  Testing application methods...")
        
        # Test display mode cycling
        initial_mode = app.display_mode
        app.cycle_display_mode()
        print(f"✅ Display mode cycle: {initial_mode.value} → {app.display_mode.value}")
        
        # Test brightness adjustment
        initial_brightness = app.display_brightness
        app.adjust_brightness()
        print(f"✅ Brightness adjust: {initial_brightness} → {app.display_brightness}")
        
        # Test logging toggle
        initial_logging = app.logging_enabled
        app.toggle_logging()
        print(f"✅ Logging toggle: {initial_logging} → {app.logging_enabled}")
        
        print("\n🎉 All integration tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mock_gps():
    """Test mock GPS functionality"""
    print("\n🛰️  Testing Mock GPS Controller")
    print("-" * 30)
    
    try:
        from tests.mock_gps import MockGPSController
        
        # Test stationary scenario
        gps = MockGPSController("stationary")
        gps.start()
        print("✅ Mock GPS controller started")
        
        # Get some NMEA sentences
        for i in range(3):
            sentence = gps.get_nmea_sentence()
            print(f"   NMEA: {sentence[:50]}..." if sentence else "   No NMEA data")
        
        # Check position data
        lat, lon, elev = gps.get_position()
        print(f"✅ Position: {lat:.6f}, {lon:.6f}, {elev:.1f}m")
        print(f"✅ Fix type: {gps.get_fix_type()}, Satellites: {gps.get_satellites()}")
        
        gps.stop()
        print("✅ Mock GPS test complete")
        return True
        
    except Exception as e:
        print(f"❌ Mock GPS test failed: {e}")
        return False

def main():
    """Run integration tests"""
    print("🚀 Pi RTK Surveyor Integration Tests")
    print("====================================\n")
    
    tests_passed = 0
    total_tests = 2
    
    # Test 1: Button Integration
    if test_button_integration():
        tests_passed += 1
    
    # Test 2: Mock GPS
    if test_mock_gps():
        tests_passed += 1
    
    # Summary
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("✅ All tests passed! Ready for next development phase.")
        return 0
    else:
        print("❌ Some tests failed. Check output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 