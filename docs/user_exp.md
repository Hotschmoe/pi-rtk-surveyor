1. user clones git repo to two Pis
2. user runs install/setup.sh to install pi-rtk-surveyor
3. user enables interfaces through rasp-config
4. user reboots

ON BOOT ONCE INSTALLED

5. screen shows splash screen for pi-rtk-surveyor initialization
6. screen prompts user BASE OR ROVER and selectable with GPIO buttons on screen

if BASE:
7. splash screen for base
8. show webserver init
9. show wifi hotspot init
10. once completed should display monitoring info
- SATs connected
- # of rovers connected
- Battery
- uptime
- # points logged

if ROVER:
7. splash screen for rover
8. show 'conencting to base' init (two part-> "found" then "connecting")
9. once connected should display monitoring info
- SATs connected
- base connected (maybe a signal strength?)
- battery
- uptime
- something to display to user when a button is pressed to log a point

BASE WEBSERVER:
- allow local devices like phones and laptops to connect to base station
- view monitoring info like battery, rovers, sats, points logged
- allow download of points to device
- stretch goal: visual topo mesh as more points get logged

====================================

GROK THOUGHTS:
GROK RECOMMENDATIONS:

I think your proposed directory structure is a solid plan. It promotes modularity by separating base-specific, rover-specific, hardware, web, and common components, which will make the project easier to maintain and scale. This aligns well with the user experience outlined in this document, focusing on a clean boot process and distinct behaviors for base and rover modes.

Suggestions:
1. Replace the current `software/` directory with `src/` to house all Python source code, keeping the structure clean.
2. Consolidate all testing, debugging, and simulation files into a single `tests/` directory at the root. Remove or archive unnecessary ones (e.g., `debug_gpio_pins.py`, `test_physical_buttons.py`, `test-integration.py`) to reduce clutter.
3. Move shared utilities (like `utils/`, `config/`, `communication/`) into `src/common/` to avoid duplication.
4. Ensure `main.py` serves as the entry point in `src/`, handling the base/rover selection logic as per the user guide.
5. Update `install/setup.sh` to reflect the new structure, and clean it by removing any testing/debug commands.
6. For screens and display logic, place shared UI elements in `src/common/display/`, with mode-specific screens in `rtk_base/` and `rtk_rover/`.
7. Review and remove redundant files from current subdirectories (e.g., merge overlapping functionality in `core/`, `monitoring/`, `services/` into common or mode-specific dirs).
8. After restructuring, update the README.md to document the new layout and usage.

Proposed File Structure:

```
pi-rtk-surveyor/
  - install/
    - setup.sh
    - systemd/
      - pi-rtk-surveyor.service
  - src/
    - hardware/
      - button_manager.py
      - oled_manager.py
      - battery_monitor.py
      - system_monitor.py
      - (other hardware init and API files, e.g., from input/, display/, monitoring/)
    - web/
      - web_server.py
      - static/
        - css/
          - style.css
        - js/
          - app.js
          - dashboard.js
      - templates/
        - base.html
        - config.html
        - dashboard.html
    - rtk_base/
      - rtk_base.py
      - base_status.py  # Screen for base monitoring
      - (other base-specific files, functions, screens)
    - rtk_rover/
      - rtk_rover.py
      - rover_status.py  # Screen for rover monitoring
      - (other rover-specific files, functions, screens)
    - common/
      - settings.py
      - device_config.json
      - nmea_parser.py
      - data_logger.py
      - coordinate_utils.py
      - (other shared files, e.g., from config/, gnss/, utils/, data_logging/)
      - display/
        - ui_elements.py
        - screens/
          - splash.py
          - menu.py
          - system_info.py
      - communication/
        - network_discovery.py
        - rtk_protocol.py
        - wifi_manager.py
    - main.py  # Entry point handling base/rover selection
  - tests/
    - (consolidated tests from software/tests/, test-data/, and root test files)
    - mock_gps.py
    - (integration tests, etc.)
  - docs/
    - current_state.py
    - raspberry-pi-setup.md
    - testing.md
    - thoughts.md
    - user_exp.md
  - scripts/
    - deploy-and-test.sh  # Cleaned up
    - hardware-test.sh
  - LICENSE
  - README.md
  - (any other root files as needed)
```

This structure trims down the convolution by centralizing tests, removing simulations, and organizing code by responsibility. If we proceed, we can implement this step by step using file moves and edits.