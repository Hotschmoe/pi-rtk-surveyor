# Pi RTK Surveyor Refactor Plan

## 🎯 Objective
Restructure the project from the current convoluted `software/` structure to a clean, modular architecture that separates base station, rover, hardware, web, and common functionality.

## 📋 Pre-Refactor Assessment

### Current Issues
- [ ] Scattered test files in root directory (`debug_gpio_pins.py`, `test_physical_buttons.py`, `test-integration.py`)
- [ ] Overlapping functionality in `software/core/`, `software/monitoring/`, `software/services/`
- [ ] No clear separation between base and rover specific code
- [ ] Confusing directory names (`software/` instead of `src/`)
- [ ] Test data and actual tests mixed together

### Target Structure
```
pi-rtk-surveyor/
├── install/
│   ├── setup.sh
│   ├── requirements.txt
│   └── systemd/
├── src/
│   ├── main.py
│   ├── hardware/
│   ├── web/
│   ├── rtk_base/
│   ├── rtk_rover/
│   └── common/
├── tests/
├── docs/
├── scripts/
└── [LICENSE, README.md, etc.]
```

## 🗂️ Phase 1: Directory Structure Creation

### 1.1 Create New Directory Structure
- [ ] Create `src/` directory
- [ ] Create `src/hardware/`
- [ ] Create `src/web/`
- [ ] Create `src/rtk_base/`
- [ ] Create `src/rtk_rover/`
- [ ] Create `src/common/`
- [ ] Create `src/common/config/`
- [ ] Create `src/common/communication/`
- [ ] Create `src/common/data_logging/`
- [ ] Create `src/common/utils/`
- [ ] Create `src/common/display/`
- [ ] Create `src/common/display/screens/`
- [ ] Create `tests/` directory
- [ ] Create `tests/integration/`
- [ ] Create `tests/hardware/`
- [ ] Create `tests/mock_data/`

### 1.2 Add __init__.py Files
- [ ] Add `src/__init__.py`
- [ ] Add `src/hardware/__init__.py`
- [ ] Add `src/web/__init__.py`
- [ ] Add `src/rtk_base/__init__.py`
- [ ] Add `src/rtk_rover/__init__.py`
- [ ] Add `src/common/__init__.py`
- [ ] Add `src/common/config/__init__.py`
- [ ] Add `src/common/communication/__init__.py`
- [ ] Add `src/common/data_logging/__init__.py`
- [ ] Add `src/common/utils/__init__.py`
- [ ] Add `src/common/display/__init__.py`
- [ ] Add `src/common/display/screens/__init__.py`

## 📦 Phase 2: File Movement and Organization

### 2.1 Move Hardware Files
- [ ] Move `software/input/button_manager.py` → `src/hardware/button_manager.py`
- [ ] Move `software/input/button_api.py` → `src/hardware/button_api.py`
- [ ] Move `software/display/oled_manager.py` → `src/hardware/oled_manager.py`
- [ ] Move `software/monitoring/battery_monitor.py` → `src/hardware/battery_monitor.py`
- [ ] Move `software/monitoring/system_monitor.py` → `src/hardware/system_monitor.py`
- [ ] Move `software/monitoring/gps_monitor.py` → `src/hardware/gps_monitor.py`

### 2.2 Move Web Files
- [ ] Move `software/web/` → `src/web/` (entire directory)
- [ ] Verify `src/web/web_server.py` exists
- [ ] Verify `src/web/static/` and `src/web/templates/` exist

### 2.3 Move RTK Base Files
- [ ] Move `software/gnss/rtk_base.py` → `src/rtk_base/rtk_base.py`
- [ ] Move `software/display/screens/base_status.py` → `src/rtk_base/base_status.py`
- [ ] Extract base-specific logic from `software/core/` → `src/rtk_base/base_core.py`

### 2.4 Move RTK Rover Files
- [ ] Move `software/gnss/rtk_rover.py` → `src/rtk_rover/rtk_rover.py`
- [ ] Move `software/display/screens/rover_status.py` → `src/rtk_rover/rover_status.py`
- [ ] Extract rover-specific logic from `software/core/` → `src/rtk_rover/rover_core.py`

### 2.5 Move Common Files
- [ ] Move `software/config/` → `src/common/config/` (entire directory)
- [ ] Move `software/communication/` → `src/common/communication/` (entire directory)
- [ ] Move `software/data_logging/` → `src/common/data_logging/` (entire directory)
- [ ] Move `software/utils/` → `src/common/utils/` (entire directory)
- [ ] Move `software/gnss/nmea_parser.py` → `src/common/nmea_parser.py`
- [ ] Move `software/gnss/lc29h_controller.py` → `src/common/lc29h_controller.py`
- [ ] Move `software/display/ui_elements.py` → `src/common/display/ui_elements.py`
- [ ] Move `software/display/screens/splash.py` → `src/common/display/screens/splash.py`
- [ ] Move `software/display/screens/menu.py` → `src/common/display/screens/menu.py`
- [ ] Move `software/display/screens/system_info.py` → `src/common/display/screens/system_info.py`
- [ ] Move `software/services/` → `src/common/services/` (entire directory)

### 2.6 Create New Entry Point
- [ ] Move `software/main.py` → `src/main.py`
- [ ] Update `src/main.py` to implement BASE/ROVER selection logic per user_exp.md

### 2.7 Consolidate Test Files
- [ ] Move `software/tests/` → `tests/integration/`
- [ ] Move `test-data/` → `tests/mock_data/`
- [ ] Review and archive/move useful parts from:
  - [ ] `debug_gpio_pins.py` → `tests/hardware/` (if useful)
  - [ ] `test_physical_buttons.py` → `tests/hardware/`
  - [ ] `test-integration.py` → `tests/integration/`

## 🔧 Phase 3: Code Updates and Fixes

### 3.1 Update Import Statements
- [ ] Update all imports in `src/hardware/` files
- [ ] Update all imports in `src/web/` files
- [ ] Update all imports in `src/rtk_base/` files
- [ ] Update all imports in `src/rtk_rover/` files
- [ ] Update all imports in `src/common/` files
- [ ] Update imports in `src/main.py`

### 3.2 Update Configuration Files
- [ ] Update `install/setup.sh` to reflect new `src/` structure
- [ ] Update `install/systemd/pi-rtk-surveyor.service` to point to `src/main.py`
- [ ] Rename `install/old_requirements.txt` → `install/requirements.txt`
- [ ] Update any hardcoded paths in configuration files

### 3.3 Update Main Entry Point
- [ ] Implement BASE/ROVER selection logic in `src/main.py`
- [ ] Add proper imports for `src.rtk_base` and `src.rtk_rover`
- [ ] Ensure splash screen logic works with new structure
- [ ] Test button selection functionality

## 🧹 Phase 4: Cleanup and Removal

### 4.1 Remove Old Structure
- [ ] Remove `software/` directory (after verifying all files moved)
- [ ] Remove root-level test files:
  - [ ] `debug_gpio_pins.py`
  - [ ] `test_physical_buttons.py`
  - [ ] `test-integration.py`
  - [ ] `run_web_server.py` (if it's a test script)

### 4.2 Remove Obsolete Files
- [ ] Remove `install/old_requirements.txt`
- [ ] Remove any duplicate or unused files discovered during move
- [ ] Clean up any `.pyc` or `__pycache__` directories

## ✅ Phase 5: Testing and Verification

### 5.1 Import Testing
- [ ] Test all imports in `src/hardware/` work correctly
- [ ] Test all imports in `src/web/` work correctly
- [ ] Test all imports in `src/rtk_base/` work correctly
- [ ] Test all imports in `src/rtk_rover/` work correctly
- [ ] Test all imports in `src/common/` work correctly

### 5.2 Functionality Testing
- [ ] Test `src/main.py` runs without import errors
- [ ] Test BASE mode selection works
- [ ] Test ROVER mode selection works
- [ ] Test OLED display initialization
- [ ] Test button functionality
- [ ] Test web server startup (base mode)

### 5.3 Service Testing
- [ ] Test `install/setup.sh` runs successfully
- [ ] Test systemd service starts correctly
- [ ] Test service points to correct `src/main.py`

### 5.4 Integration Testing
- [ ] Test full boot sequence with BASE selection
- [ ] Test full boot sequence with ROVER selection
- [ ] Test hardware initialization
- [ ] Test display screens work in both modes

## 📚 Phase 6: Documentation Updates

### 6.1 Update Documentation
- [ ] Update README.md to reflect new structure
- [ ] Update any documentation referencing old paths
- [ ] Create new architecture documentation if needed

### 6.2 Update Scripts
- [ ] Update `scripts/deploy-and-test.sh` for new structure
- [ ] Update `scripts/hardware-test.sh` for new structure
- [ ] Update any other scripts referencing old paths

## 🎉 Phase 7: Final Verification

### 7.1 Pre-Deployment Checklist
- [ ] All imports work correctly
- [ ] No references to old `software/` directory remain
- [ ] Service file points to correct entry point
- [ ] Setup script works with new structure
- [ ] BASE/ROVER selection functions correctly
- [ ] All hardware components initialize properly

### 7.2 Git Cleanup
- [ ] Commit all changes
- [ ] Update .gitignore if needed
- [ ] Verify no important files were accidentally deleted
- [ ] Tag this refactor commit for easy rollback if needed

## 🚨 Rollback Plan
If issues arise during refactor:
1. Restore from git backup before refactor started
2. Identify specific failing component
3. Fix incrementally rather than rolling back entire refactor
4. Document any discovered issues for future reference

## 📝 Notes
- Test each phase thoroughly before proceeding to next
- Keep backup of working version before starting
- Update this checklist as issues are discovered
- Document any deviations from plan
