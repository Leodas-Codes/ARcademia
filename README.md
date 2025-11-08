# ARcademia — VR Loader & AR Streamer

A desktop-style Python application for loading, displaying, and streaming 3D CAD models with Virtual AR preview capabilities.

## Features

- **3D Model Loading**: Load and display .STL and .OBJ files
- **Interactive 3D Viewport**: Orbit, pan, and zoom controls
- **Multi-Model Scene**: Add multiple models to a single scene
- **Virtual AR Preview**: Standalone preview window with ground plane
- **AI Voice-Over**: Text-to-speech descriptions of CAD models with dimensional analysis
- **UDP Streaming**: Stream models to AR devices over the network
- **Real-time Statistics**: View vertex and triangle counts
- **Keyboard Shortcuts**:
  - `B` - Toggle back-face culling
  - `L` - Toggle axes display
  - `R` - Re-frame scene to fit models
  - `S` - Take screenshot
  - `DEL` - Remove selected model

## Quick Start

1. Click the "Run" button to launch the application
2. The VNC desktop window will open with the ARcademia GUI
3. Place your .STL or .OBJ files in the `cad_files` folder
4. Click "Refresh List" to see your models
5. Select a model and click "Display Model" to view it
6. Use "Add To Scene" to add multiple models
7. Click "Virtual AR Preview" to see an AR-style preview

## Controls

### Mouse Controls
- **Left Click + Drag**: Orbit around the model
- **Right Click + Drag**: Pan the camera
- **Scroll Wheel**: Zoom in/out

### GUI Buttons
- **Choose Folder**: Select a different model directory
- **Refresh List**: Reload the file list
- **Display Model**: Clear scene and show selected model
- **Add To Scene**: Add selected model to current scene
- **Remove Selected**: Remove the selected model from scene
- **Virtual AR Preview**: Open AR preview window
- **🔊 Describe Model**: AI voice-over explaining the selected model's dimensions and features
- **🔊 Describe Scene**: AI voice-over describing all models in the current scene

## Technical Requirements

- Python 3.11
- Open3D ≥ 0.19.0
- NumPy ≥ 1.24.0
- pyttsx3 ≥ 2.90 (for voice-over)
- espeak (system TTS engine)
- VNC/Desktop mode (automatically configured)

## Project Structure

```
.
├── main.py              # Main application
├── requirements.txt     # Python dependencies
├── cad_files/          # Place your 3D models here
│   └── sample_cube.stl # Sample model for testing
├── screenshots/        # Auto-generated screenshots
└── README.md           # This file
```

## Adding Your Own Models

1. Place .STL or .OBJ files in the `cad_files` directory
2. Click "Refresh List" in the application
3. Your models will appear in the file list

## AI Voice-Over Feature

The application includes an intelligent voice-over system that analyzes and verbally describes your CAD models:

**What it analyzes:**
- Model name and file format
- Vertex and triangle counts (mesh complexity)
- Precise dimensions (width, height, depth in units)
- Volume calculation (for watertight solids)
- Surface area measurements
- Model type (solid vs. surface)

**How to use:**
1. **Single Model Description**: Select a model and click "🔊 Describe Model" to hear a detailed analysis
2. **Scene Description**: Click "🔊 Describe Scene" to hear an overview of all models currently displayed

The AI will speak comprehensive information about your CAD models, helping you understand their properties without reading numbers from the screen. This is especially useful for:
- Quick dimensional verification
- Accessibility features
- Presentations and demonstrations
- Educational purposes

## Network Streaming

The application includes UDP streaming for AR devices:

1. Enter the AR device IP address
2. Enter the port number (default: 51234)
3. Display the models you want to stream
4. Use the streaming functionality for network transmission

## Troubleshooting

- **Models not appearing**: Click "Refresh List" after adding new files
- **GUI not visible**: Ensure VNC mode is enabled in Replit
- **Loading errors**: Check that your files are valid .STL or .OBJ format

## License

Built with Open3D - see Open3D license for details.
