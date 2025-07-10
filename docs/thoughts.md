# Pi RTK Surveyor - Software Architecture & Thoughts

## Project Overview
DIY cm-accurate RTK surveying system using dual Raspberry Pi Zero W 2 units with LC29H GNSS HATs and Waveshare 1.3" OLED displays.

## User Workflow

### Setup Phase
1. **Power On Both Units**
   - Boot sequence with splash screen
   - Hardware detection and initialization
   - Display startup diagnostics

2. **Device Role Selection**
   - OLED menu: "Select Mode: 1) Base Station  2) Rover"
   - Button navigation to select role
   - Configuration saved for session

3. **Base Station Setup**
   - Position on tripod at known/measured point
   - Start GNSS acquisition and averaging
   - Begin broadcasting RTK corrections via WiFi hotspot
   - Display: GPS status, connected rovers, uptime

4. **Rover Setup** 
   - Connect to base station WiFi network
   - Receive RTK corrections
   - Display: GPS accuracy, fix type, battery level
   - Ready for survey points collection

### Survey Phase
1. **Rover Operation**
   - Walk around property with rover on survey pole
   - Real-time display: coordinates, accuracy, fix status
   - Press button to log survey point when positioned
   - Visual/audio feedback on point capture
   - Continue until survey complete

2. **Data Collection**
   - Each point logged with: timestamp, lat/lon/elevation, accuracy
   - Points numbered sequentially
   - CSV format for easy CAD import

### Data Export Phase
1. **Survey Completion**
   - Stop logging, show summary (total points, time, etc.)
   - Prepare data for transfer

2. **Data Transfer Options**
   - Web interface for download
   - USB mass storage mode
   - WiFi file transfer to PC

## Software Architecture

### Core File Structure
```
pi-rtk-surveyor/
├── software/
│   ├── main.py                 # Main application entry point
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py         # Configuration management
│   │   └── device_config.json  # Device-specific settings
│   ├── core/
│   │   ├── __init__.py
│   │   ├── application.py      # Main app controller
│   │   ├── state_manager.py    # Application state management
│   │   └── device_manager.py   # Hardware abstraction
│   ├── display/
│   │   ├── __init__.py
│   │   ├── oled_manager.py     # OLED display controller
│   │   ├── screens/            # Different display screens
│   │   │   ├── __init__.py
│   │   │   ├── splash.py       # Boot splash screen
│   │   │   ├── menu.py         # Mode selection menu
│   │   │   ├── base_status.py  # Base station status
│   │   │   ├── rover_status.py # Rover status
│   │   │   └── system_info.py  # System monitoring
│   │   └── ui_elements.py      # Reusable UI components
│   ├── input/
│   │   ├── __init__.py
│   │   ├── button_manager.py   # Button event handling
│   │   └── button_api.py       # Button API for other modules
│   ├── gnss/
│   │   ├── __init__.py
│   │   ├── lc29h_controller.py # LC29H GNSS HAT interface
│   │   ├── rtk_base.py         # RTK base station logic
│   │   ├── rtk_rover.py        # RTK rover logic
│   │   └── nmea_parser.py      # NMEA sentence parsing
│   ├── communication/
│   │   ├── __init__.py
│   │   ├── wifi_manager.py     # WiFi setup and management
│   │   ├── rtk_protocol.py     # RTK correction protocol
│   │   └── network_discovery.py # Base station discovery
│   ├── logging/
│   │   ├── __init__.py
│   │   ├── data_logger.py      # Survey point logging
│   │   ├── system_logger.py    # System event logging
│   │   └── export_manager.py   # Data export utilities
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── system_monitor.py   # CPU, memory, temperature
│   │   ├── battery_monitor.py  # Battery level and estimation
│   │   └── gps_monitor.py      # GPS status and quality
│   ├── web/
│   │   ├── __init__.py
│   │   ├── web_server.py       # Flask web interface
│   │   ├── templates/          # HTML templates
│   │   └── static/             # CSS, JS files
│   ├── services/
│   │   ├── __init__.py
│   │   ├── startup.py          # System startup script
│   │   └── shutdown.py         # Clean shutdown handling
│   └── utils/
│       ├── __init__.py
│       ├── coordinate_utils.py # Coordinate transformations
│       ├── file_utils.py       # File operations
│       └── validation.py       # Data validation
├── install/
│   ├── setup.sh               # Main installation script
│   ├── systemd/
│   │   └── pi-rtk-surveyor.service # Systemd service file
│   └── requirements.txt       # Python dependencies
└── data/
    ├── surveys/               # Survey data storage
    ├── logs/                  # System logs
    └── config/                # Runtime configuration
```

## Technical Considerations

### RTK Communication
- **Base Station**: Creates WiFi hotspot "RTK-BASE-XXXX"
- **Rover**: Connects to base station hotspot
- **Protocol**: RTCM3 corrections over TCP/UDP
- **Range**: Standard WiFi ~100-150m (330-490 feet)
- **Extended Range Options**:
  - External antennas: 200-300m range
  - WiFi repeater: Full 10-acre coverage
  - Multi-position base: Move base station 2-3 times for large parcels
- **Fallback**: Option to connect both units to existing WiFi network

### Display Management
- **Multi-threading**: Separate thread for display updates
- **Screen Modes**: 
  - Status (default): GPS info, accuracy, battery
  - System: CPU temp, memory, load average
  - Survey: Point count, current coordinates
  - Menu: Navigation and settings
- **Button Controls**:
  - KEY1: Mode selection / Menu navigation
  - KEY2: Settings / Brightness / Volume
  - KEY3: Point logging / Action button
  - Joystick: Navigation in menus

### Data Management
- **Survey Points**: CSV format with headers
  ```csv
  Point_ID,Timestamp,Latitude,Longitude,Elevation,Accuracy_H,Accuracy_V,Fix_Type
  001,2024-01-15T10:30:45,40.7128,-74.0060,10.5,0.02,0.03,RTK_FIXED
  ```
- **Auto-backup**: Duplicate data to prevent loss
- **Export Formats**: CSV, GPX, KML options

### System Integration
- **Startup Service**: Systemd service for auto-start
- **Clean Shutdown**: GPIO button for safe power-off
- **Error Handling**: Graceful degradation, error logging
- **Recovery**: Auto-restart on critical failures

### Power Management
- **Battery Monitoring**: Real-time voltage/percentage
- **Low Power Mode**: Reduce display brightness, GPS update rate
- **Sleep/Wake**: Automatic sleep after inactivity
- **Shutdown Timer**: Configurable auto-shutdown

## Development Phases

### Phase 1: Core Infrastructure ✅
- [x] Basic OLED display functionality
- [x] Button input handling
- [x] System monitoring
- [x] Configuration management

### Phase 2: GNSS Integration (Current)
- [ ] LC29H HAT communication
- [ ] NMEA parsing and GPS data
- [ ] Basic positioning display
- [ ] GPS status monitoring

### Phase 3: RTK Implementation
- [ ] Base station mode
- [ ] Rover mode with corrections
- [ ] WiFi communication setup
- [ ] RTK accuracy validation

### Phase 4: Survey Application
- [ ] Point logging system
- [ ] Survey session management
- [ ] Data export functionality
- [ ] Field operation UI

### Phase 5: Web Interface & Polish
- [ ] Web-based data download
- [ ] Survey visualization
- [ ] System configuration UI
- [ ] Documentation and testing

## Practical Considerations for 10-Acre Parcel

### Survey Strategy for Large Properties
- **Parcel Size**: 10 acres ≈ 660' x 660' (934' diagonal)
- **Terrain**: 5% slope (40' elevation change over 660') - **elevation helps with line of sight!**
- **Communication Challenge**: 934' diagonal exceeds standard WiFi range

### Range Extension Solutions (Hobby-Friendly)
1. **External Antennas** (~$10-15 each)
   - 2.4GHz directional antennas on both units
   - Can achieve 600-900 foot range with clear line of sight
   - Easy to mount on survey poles/tripods

2. **WiFi Repeater Method** (~$20-30)
   - Place battery-powered repeater at property center
   - Extends range to cover full 10-acre area
   - Position for best line of sight to both corners

3. **Multi-Position Base Strategy** (No additional cost)
   - Survey property in 2-3 sections
   - Move base station to different corners
   - Overlap areas for accuracy validation
   - Most reliable for hobby use

### Multi-Section Survey Workflow for Large Properties

#### Dividing Property into Sections
For a 10-acre parcel (660' x 660'), divide into 4 overlapping sections:

```
Section Layout (Top View):
┌─────────────────────────────────────┐
│  A1    │    A2    │  200' overlap  │
│  Base1 │          │     zones      │
│        │   ◄──────┼──────►         │
├────────┼──────────┼────────────────┤
│        │   ◄──────┼──────►         │
│  B1    │    B2    │                │
│  Base3 │          │    Base4       │
└─────────────────────────────────────┘
```

#### Step-by-Step Multi-Section Process

1. **Section A1 (Southwest Corner)**
   - Place base station at A1 corner
   - Survey 400' x 400' area around base
   - Log 15-20 perimeter points + key features
   - Include 100' overlap into adjacent sections
   - Mark base position as "BASE_A1" reference point

2. **Section A2 (Southeast Corner)**  
   - Move base to A2 position
   - Re-survey 5-10 overlap points from A1 for validation
   - Survey new 400' x 400' area
   - Log perimeter + features + overlap verification
   - Mark base position as "BASE_A2"

3. **Sections B1 & B2 (North Side)**
   - Repeat process for northern sections
   - Always re-survey overlap points for continuity
   - Maintain 100' overlap between all sections

#### Post-Processing Data Combination

**Software Workflow:**
1. **Data Validation**
   - Compare overlap point coordinates between sections
   - Typical variance should be <5cm for good surveys
   - Flag any points with >10cm discrepancy for re-survey

2. **Coordinate System Alignment**
   ```python
   # Pseudo-code for data merging
   section_a1 = load_survey_data("section_a1.csv")
   section_a2 = load_survey_data("section_a2.csv") 
   
   # Find common overlap points
   overlap_points = find_matching_coordinates(section_a1, section_a2, tolerance=0.05)
   
   # Calculate transformation if needed
   transform = calculate_coordinate_adjustment(overlap_points)
   
   # Merge datasets with overlap verification
   combined_survey = merge_sections([section_a1, section_a2, section_b1, section_b2])
   ```

3. **Quality Control Output**
   - Generate overlap accuracy report
   - Create visualization showing section boundaries
   - Export final combined dataset as single CSV
   - Include survey metadata (base positions, dates, accuracy)

#### Benefits of Multi-Section Approach
✅ **Guaranteed Coverage**: No range limitations  
✅ **Higher Accuracy**: Each section gets optimal RTK signal  
✅ **Built-in Validation**: Overlap areas verify accuracy  
✅ **Flexible Timing**: Survey sections on different days  
✅ **Error Recovery**: Re-survey individual sections if needed  

### Future Long-Distance Communication: LoRa Integration

**LoRa Module Integration (Future Development)**
- **Range**: 2-5 miles line-of-sight vs 300' WiFi
- **Accuracy Trade-off**: LoRa introduces 5-15cm additional uncertainty
  - Lower data rate = less frequent corrections
  - Longer transmission delays = reduced real-time accuracy
  - Still suitable for property mapping (not precision construction)

**When to Consider LoRa:**
- Properties >20 acres where section overlap becomes impractical
- Mountainous terrain where WiFi repeaters won't work
- Survey applications where 10-20cm accuracy is acceptable
- Remote areas without existing WiFi infrastructure

**LoRa Implementation Notes:**
```
Hardware Addition: ~$15-25 per unit
- 915MHz LoRa modules (SX1276/RFM95W)
- External antenna for better range
- Reduced RTK update rate (1Hz vs 5Hz WiFi)
```

### Additional Hardware for 10-Acre Surveys
| Item | Purpose | Cost | Priority |
|------|---------|------|----------|
| **External WiFi Antennas** | Extended range | $10-15 each | High |
| **WiFi Range Extender** | Full area coverage | $20-30 | Medium |
| **Survey Pole/Bipod** | Rover stability | $15-25 | High |
| **Weatherproof Cases** | Field protection | $20-30 each | Medium |
| **Extra Battery Packs** | Extended operation | $20-30 each | Medium |
| **Data Backup USB** | Survey data safety | $10-15 | Low |

### Why This Project is Perfect for Hobby Use
✅ **Achievable Complexity**: Professional techniques, DIY-friendly implementation  
✅ **Scalable Accuracy**: 2-5cm accuracy perfect for property mapping  
✅ **Cost Effective**: $200-300 total vs $2000+ professional survey  
✅ **Educational**: Learn surveying principles hands-on  
✅ **Reusable**: Survey multiple properties, help neighbors  
✅ **Expandable**: Start basic, add features over time  

### Hobby vs Professional Compromises
- **Accuracy**: ±2-5cm vs ±1cm (perfectly acceptable for topo mapping)
- **Range**: Sectioned surveys vs single setup (actually more thorough!)
- **Speed**: Slower setup vs professional efficiency (learning experience!)
- **Certification**: Non-legal vs survey-grade (hobby use only)

## Next Immediate Steps
1. Create the basic file structure
2. Implement modular button API
3. Set up LC29H communication
4. Test basic GNSS data acquisition
5. Develop WiFi communication for RTK corrections
6. Test range with external antennas for 10-acre coverage
