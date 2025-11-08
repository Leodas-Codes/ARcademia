# ARcademia — VR Loader & AR Streamer

## Overview
ARcademia is a desktop-style Python application built with Open3D for loading, displaying, and streaming 3D CAD models. The application features a modern GUI interface with interactive 3D visualization, Virtual AR Preview capabilities, and UDP streaming for AR devices.

## Project Architecture

### Technology Stack
- **Python**: 3.11
- **Open3D**: ≥0.19.0 (3D visualization and GUI)
- **NumPy**: ≥1.24.0 (numerical operations)
- **pyttsx3**: ≥2.90 (text-to-speech for AI voice-over)
- **Display**: VNC/Desktop mode (required for GUI rendering)

### Project Structure
```
.
├── main.py              # Main application entry point
├── requirements.txt     # Python dependencies
├── cad_files/          # Directory for 3D model files (.STL, .OBJ)
├── screenshots/        # Auto-generated screenshots (S key)
├── replit.md           # Project documentation
└── .gitignore          # Git ignore patterns
```

### Key Features
1. **3D Model Loading**: Supports .STL and .OBJ file formats
2. **Interactive 3D Viewport**: Orbit, pan, zoom controls
3. **Model Management**: Display, add to scene, remove individual models
4. **Virtual AR Preview**: Standalone window with ground plane and camera positioning
5. **AI Voice-Over**: Intelligent text-to-speech that analyzes and describes CAD models based on:
   - Dimensional measurements (width, height, depth)
   - Mesh complexity (vertices, triangles)
   - Volume and surface area calculations
   - Model type (solid vs. surface)
6. **UDP Streaming**: Network streaming capability for AR devices
7. **View Controls**: Toggle axes, double-sided rendering, back-face culling
8. **Keyboard Shortcuts**:
   - `B`: Toggle back-face culling
   - `L`: Toggle axes display
   - `R`: Re-frame scene to fit models
   - `S`: Take screenshot
   - `DEL`: Remove selected model
9. **Scene Statistics**: Real-time vertex and triangle count display
10. **Auto-refresh**: Directory monitoring for new models

## System Dependencies
The following system packages are required for Open3D GUI to function in Replit:
- **udev**: Device management library
- **X11 libraries**: xorg.libX11, xorg.libXcursor, xorg.libXrandr, xorg.libXi, xorg.libXext, xorg.libXfixes, xorg.libXrender, xorg.libXinerama
- **OpenGL**: mesa, libGL
- **libgcc**: Required for libgomp (OpenMP runtime)
- **espeak**: Text-to-speech engine for voice-over functionality

These are automatically configured in the Replit environment and should persist across sessions.

## Recent Changes
- **2025-01-08**: Added AI Voice-Over Feature
  - Integrated pyttsx3 for text-to-speech functionality
  - Added intelligent model analysis system that extracts:
    - Dimensional measurements (width, height, depth)
    - Mesh statistics (vertices, triangles, surface area)
    - Volume calculations for watertight solids
  - Created natural language description generator
  - Added "Describe Model" and "Describe Scene" voice-over controls to GUI
  - Thread-safe TTS implementation to prevent GUI blocking
  - Installed espeak system dependency for Linux TTS support

- **2025-01-08**: Initial project setup
  - Adapted Windows-based code for Replit environment
  - Changed model directory from `D:\Repli\caed_files` to `./cad_files`
  - Configured VNC workflow for desktop GUI rendering
  - Installed Python 3.11 with Open3D ≥0.19.0
  - Installed required system dependencies (udev, X11, OpenGL, libgcc)
  - Created project structure and documentation
  - Added sample cube model for immediate testing

## Running the Application
The application runs automatically in VNC/Desktop mode when you click "Run". The GUI window will appear with:
- Left panel: 3D viewport for model visualization
- Right panel: File browser, controls, and settings

## User Preferences
- None specified yet

## Configuration
- **Models Directory**: `./cad_files` (configurable via GUI)
- **Default AR IP**: 192.168.0.10
- **Default AR Port**: 51234
- **Supported Formats**: .STL, .OBJ
- **Window Size**: 1280x800 (main), 1000x700 (AR preview)

## Notes
- The application requires VNC/Desktop mode to display the Open3D GUI
- Models must be placed in the `cad_files` directory or chosen via the folder picker
- UDP streaming is available but not active by default (requires manual trigger)
- Compatible with Open3D 0.18 and 0.19+ through version-safe API usage
