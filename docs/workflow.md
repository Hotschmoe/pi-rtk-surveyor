graph TD
    A["🚀 Boot"] --> B["💫 Splash Screen<br/>(3 seconds)"]
    B --> C["📋 Menu Screen<br/>Select Mode:<br/>1) Base Station<br/>2) Rover<br/>KEY1/2 to select"]
    
    C -->|"KEY1"| D["🏗️ Base Init 1/3<br/>Base Station Mode"]
    D --> E["🌐 Base Init 2/3<br/>Starting Web Server..."]
    E --> F["📡 Base Init 3/3<br/>Starting WiFi Hotspot..."]
    F --> G["📊 Base Monitoring<br/>SATs: X | Rovers: Y<br/>Batt: Z% | Up: Wh<br/>Points: P"]
    
    C -->|"KEY2"| H["🚁 Rover Init 1/2<br/>Rover Mode"]
    H --> I["🔍 Rover Init 2/2<br/>Searching for base..."]
    I --> J["✅ Rover Init 2/2<br/>Base found! Connecting..."]
    J --> K["📡 Rover Monitoring<br/>SATs: X | Base: OK<br/>Signal: Y% | Batt: Z%<br/>Up: Wh | Ready"]
    
    G -->|"KEY1"| C
    K -->|"KEY1"| C
    C -->|"KEY3"| L["⚙️ System Info<br/>CPU: X°C<br/>Memory: Y%<br/>Battery: Z%"]
    L -->|"KEY1"| C
    
    K -->|"KEY3"| M["📍 Point Logged<br/>Counter++"]
    M --> K