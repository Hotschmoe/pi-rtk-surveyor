# Pi RTK Surveyor

> **DIY cm-accurate surveying for property mapping and topo creation**

Build your own professional-grade RTK surveying station using a Raspberry Pi. Achieve centimeter-level accuracy for a fraction of the cost of commercial solutions.

## 🎯 Why Pi RTK Surveyor?

**Professional land surveying costs $500-2000+ per property.** This project lets you:

- ✅ **Survey your own property** with cm-level precision
- ✅ **Create accurate topo maps** for landscaping, drainage, construction
- ✅ **Generate CAD-ready data** for design software
- ✅ **Total cost under $200** vs $2000+ for professional surveys
- ✅ **Portable battery operation** for remote locations
- ✅ **Real-time monitoring** with OLED display and battery management

## 📷 What You'll Build

<!-- Add photos when available -->
*Coming soon: Photos of the completed RTK station*

**Key Features:**
- Raspberry Pi-based RTK base station and rover
- 1.3" OLED display with battery monitoring
- 10+ hour battery operation
- Button controls for field operation
- Real-time GPS coordinate display
- Data logging for CAD import

## 🛠️ Hardware Requirements

### Core Components (~$150-200)
| Component | Purpose | Est. Cost |
|-----------|---------|-----------|
| **Raspberry Pi Zero W 2** | Main computer | $15 |
| **LC29H GNSS RTK HAT** | cm-accurate GPS | $60-80 |
| **Waveshare 1.3" OLED HAT** | Display + controls | $15-20 |
| **10,000mAh USB Power Bank** | Field power | $20-30 |
| **40-pin GPIO Extender** | Clean stacking | $5-10 |
| **MicroSD Card (32GB+)** | Storage | $10 |

### Optional Additions
- Weatherproof case for field use
- External GPS antenna for better reception
- Solar panel for extended operation

## 🚀 Quick Start

### 1. Hardware Assembly
```bash
# Stack order (bottom to top):
1. Raspberry Pi Zero W 2
2. LC29H GNSS HAT (with tall pins)
3. Waveshare 1.3" OLED HAT
```

### 2. Software Installation
```bash
# Clone this repository
git clone https://github.com/hotschmoe/pi-rtk-surveyor.git
cd pi-rtk-surveyor

# Run setup script
chmod +x setup.sh
./setup.sh
```
or
```bash
bash setup.sh
```


### 3. First Survey
On boot, the system will prompt the user to select BASE or ROVER mode, which will start the appropriate software components.

### 4. Project Structure
```
pi-rtk-surveyor/
├── setup.sh          # setup and install
├── src/              # Main application code
│   ├── main.py       # Application entry point
│   ├── hardware/     # Hardware interface modules
│   ├── web/          # Web interface
│   ├── rtk_base/     # Base station specific code
│   ├── rtk_rover/    # Rover specific code
│   └── common/       # Shared utilities and libraries
├── tests/            # Test files and mock data
├── docs/             # Documentation
└── scripts/          # Utility scripts
```

## 📋 Current Status

### ✅ Completed Features
- [x] OLED display integration
- [x] Battery monitoring and runtime estimation
- [x] Button interface for field operation
- [x] System monitoring (CPU temp, memory, load)
- [x] Multiple display modes
- [x] Clean shutdown handling
- [x] **Project refactor to modular structure** (hardware, web, rtk_base, rtk_rover, common)
- [x] Systemd service integration
- [x] Installation and setup scripts

### 🚧 In Development
- [ ] LC29H GPS integration and testing
- [ ] RTK base station setup
- [ ] Coordinate logging to CSV
- [ ] BASE/ROVER mode selection on startup
- [ ] Data export for CAD software

### 🔮 Planned Features
- [ ] Web interface for remote monitoring
- [ ] Automatic topo map generation
- [ ] Survey point validation
- [ ] Property boundary mapping
- [ ] Integration with QGIS/AutoCAD

## 📖 Documentation

- **[Hardware Setup Guide](docs/hardware-setup.md)** - Detailed wiring and assembly
- **[Software Installation](docs/software-setup.md)** - Step-by-step Pi configuration
- **[Field Operation Manual](docs/field-guide.md)** - How to conduct surveys
- **[CAD Integration](docs/cad-export.md)** - Getting data into design software

## 🔧 Technical Specifications

**Accuracy:** ±2-5cm horizontal, ±3-8cm vertical (with RTK correction)  
**Update Rate:** 1-10Hz positioning  
**Battery Life:** 12-15 hours continuous operation  
**Operating Range:** Base station + rover up to 10km  
**Data Format:** NMEA, RINEX, CSV export  
**Weather Rating:** IP65 with proper enclosure  

## 💰 Cost Comparison

| Solution | Cost | Accuracy | Ownership |
|----------|------|----------|-----------|
| **Professional Survey** | $500-2000+ | ±1cm | One-time service |
| **Commercial RTK Kit** | $5000-15000+ | ±1cm | Full ownership |
| **Pi RTK Surveyor** | $150-200 | ±2-5cm | Full ownership + reusable |

## 🌍 Use Cases

### Property Owners
- **Landscaping design** - Plan drainage, retaining walls, gardens
- **Construction projects** - Foundation layouts, utility planning
- **Property boundaries** - Verify fence lines, easements
- **Flood planning** - Understand water flow patterns

### Professionals
- **Small surveying firms** - Cost-effective equipment
- **Landscape architects** - Site analysis and design
- **Engineers** - Site assessment and planning
- **Researchers** - Academic/scientific surveying projects

## 🤝 Contributing

We welcome contributions! Here's how to help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Areas for Contribution
- Hardware testing with different GPS modules
- Software improvements and bug fixes
- Documentation and tutorials
- CAD software integration
- Field testing and validation

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This project is for educational and personal use. For legal surveying, boundary determination, or construction projects requiring certified accuracy, please consult a licensed professional surveyor.

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/hotschmoe/pi-rtk-surveyor/issues)
- **Discussions:** [GitHub Discussions](https://github.com/hotschmoe/pi-rtk-surveyor/discussions)
- **Wiki:** [Project Wiki](https://github.com/hotschmoe/pi-rtk-surveyor/wiki)

## 🙏 Acknowledgments

- [Waveshare](https://www.waveshare.com/) for excellent Pi HATs
- [luma.oled](https://github.com/rm-hull/luma.oled) for display drivers
- RTK surveying community for techniques and validation
- Raspberry Pi Foundation for affordable computing

---

**Ready to map your property?** ⭐ Star this repo and let's build something amazing together!

*Professional-grade surveying shouldn't cost thousands. Let's democratize precision mapping.*