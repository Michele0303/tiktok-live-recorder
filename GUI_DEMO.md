# TikTok Live Recorder - GUI Demo Script

This demonstrates the new GUI and CLI launcher functionality.

## Usage Examples

### GUI Mode (New!)
```bash
# Launch the modern GUI interface
python launcher.py --gui

# Alternative direct launch
python gui_main.py
```

### CLI Mode (Traditional)
```bash
# Using the new launcher
python launcher.py -user @username -mode automatic

# Direct CLI (still works)
python main.py -user @username -mode automatic
```

### Help and Options
```bash
# Show unified help
python launcher.py --help

# Show traditional CLI help
python launcher.py -h
```

## GUI Features Showcase

The new GUI includes:

1. **📺 Source Tab**: Easy input for URL/username/room ID
2. **⚙️ Settings Tab**: Output directory, duration, Telegram upload
3. **🔧 Advanced Tab**: Proxy settings and update preferences
4. **📝 Output Log**: Real-time logging and status updates
5. **🎯 Progress Monitoring**: Visual progress indication

## Technical Benefits

- **Non-blocking UI**: Recording runs in separate threads
- **Real-time Updates**: Live status and progress reporting
- **Input Validation**: Prevents common user errors
- **Modern Design**: Clean, professional interface
- **Full Compatibility**: Works alongside existing CLI

## Installation

No additional steps needed! PyQt6 is included in requirements.txt

The GUI works on Windows, Linux, and macOS with Python 3.8+