# TikTok Live Recorder GUI

This document describes the new GUI (Graphical User Interface) feature for TikTok Live Recorder.

## Features

The GUI provides a modern, user-friendly interface with the following features:

### 📺 Source Configuration
- **Multiple Input Methods**: Support for TikTok URL, username, or room ID
- **Radio Button Selection**: Easy switching between input methods
- **Real-time Validation**: Input validation with user-friendly error messages

### ⚙️ Recording Settings
- **Recording Modes**: Manual and Automatic recording modes
- **Automatic Interval**: Configurable check interval for automatic mode
- **Output Directory**: Browse and select custom output directories
- **Duration Limiting**: Optional recording duration limits
- **Telegram Upload**: Easy toggle for post-recording Telegram upload

### 🔧 Advanced Features
- **Proxy Support**: HTTP/HTTPS proxy configuration
- **Update Checking**: Configurable update checking
- **Real-time Logging**: Live output display with color-coded messages
- **Progress Monitoring**: Visual progress indication during recording

### 🎨 User Experience
- **Modern Design**: Clean, intuitive interface with modern styling
- **Tabbed Layout**: Organized configuration in logical tabs
- **Responsive UI**: Non-blocking interface with threaded operations
- **Status Updates**: Real-time status updates and progress indication

## Installation

The GUI requires PyQt6, which is automatically included in the requirements:

```bash
pip install -r requirements.txt
```

## Usage

### Option 1: Universal Launcher (Recommended)
```bash
# Launch GUI mode
python launcher.py --gui

# Launch CLI mode (traditional)
python launcher.py -user @username -mode automatic

# Show help
python launcher.py --help
```

### Option 2: Direct GUI Launch
```bash
python gui_main.py
```

### Option 3: Traditional CLI
```bash
python main.py -user @username -mode automatic
```

## GUI Components

### Source Tab
- **TikTok Live URL**: Direct URL input for live streams
- **Username**: TikTok username input (with or without @)
- **Room ID**: Direct room ID input for advanced users
- **Recording Mode**: Manual or Automatic recording selection
- **Check Interval**: Automatic mode polling interval (1-60 minutes)

### Settings Tab
- **Output Directory**: Custom directory selection with browse button
- **Duration Limit**: Optional recording time limit with checkbox
- **Telegram Upload**: Toggle for automatic Telegram upload

### Advanced Tab
- **Proxy Settings**: HTTP/HTTPS proxy configuration
- **Update Checking**: Enable/disable automatic update checks

### Output Log
- **Real-time Logging**: Live display of recording progress and status
- **Clear Function**: Clear log output for better readability
- **Status Bar**: Quick status indication at the bottom

## Technical Implementation

### Architecture
- **PyQt6 Framework**: Modern Qt6 bindings for Python
- **Threaded Operations**: Non-blocking UI with worker threads
- **Signal/Slot Communication**: Efficient event handling
- **Integration**: Seamless integration with existing CLI codebase

### Threading Model
- **Main Thread**: GUI operations and user interaction
- **Worker Thread**: Recording operations to prevent UI blocking
- **Signal Communication**: Safe cross-thread communication

### Error Handling
- **Input Validation**: Real-time input validation with user feedback
- **Exception Handling**: Graceful error handling with user notifications
- **Recovery**: Safe recovery from errors without crashing

## Screenshots

![TikTok Live Recorder GUI](../gui_screenshot.png)

*The modern, tabbed interface provides easy access to all recording features*

## Compatibility

### Operating Systems
- **Windows**: Full support with native styling
- **Linux**: Full support with Qt6 libraries
- **macOS**: Compatible with PyQt6 installation

### Python Versions
- **Python 3.8+**: Recommended for best compatibility
- **PyQt6**: Automatically installed with requirements

### Display Requirements
- **GUI Mode**: Requires display (X11, Wayland, or Windows)
- **Headless Mode**: Use CLI mode for headless environments

## Development

### Code Structure
```
src/
├── gui/
│   ├── __init__.py
│   ├── main_window.py       # Main GUI implementation
│   └── widgets/
│       └── __init__.py      # Custom widgets (future expansion)
├── gui_main.py              # GUI entry point
├── launcher.py              # Universal launcher
└── main.py                  # Original CLI entry point
```

### Adding Features
The GUI is designed for extensibility:
- **Custom Widgets**: Add to `gui/widgets/` directory
- **New Tabs**: Extend `create_*_tab()` methods
- **Additional Settings**: Integrate with existing args system

## Troubleshooting

### Common Issues

**GUI Won't Start**
```bash
# Install missing dependencies
sudo apt install -y qt6-base-dev libegl1 libxcb-cursor0

# Or use offscreen mode for testing
QT_QPA_PLATFORM=offscreen python gui_main.py
```

**Import Errors**
```bash
# Ensure PyQt6 is installed
pip install PyQt6

# Check Python path
python -c "import PyQt6; print('PyQt6 OK')"
```

**Threading Issues**
- The GUI uses proper threading to prevent blocking
- All recorder operations run in separate worker threads
- Use the stop button to safely terminate recording

### Debug Mode
For debugging, you can enable verbose logging:
```bash
# Enable debug output
export QT_LOGGING_RULES="qt.qpa.plugin.debug=true"
python launcher.py --gui
```

## Future Enhancements

Planned improvements for future versions:
- **Dark Mode**: Theme switching support
- **Multi-user Recording**: GUI support for multiple simultaneous recordings
- **Recording History**: Built-in recording history and management
- **Advanced Scheduling**: Recording scheduler with calendar interface
- **Plugin System**: Extensible plugin architecture for custom features

## Contributing

To contribute to the GUI:
1. Follow the existing code style and structure
2. Test GUI changes in both windowed and headless environments
3. Ensure compatibility with existing CLI functionality
4. Add appropriate error handling and user feedback
5. Update documentation for new features