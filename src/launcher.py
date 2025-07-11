#!/usr/bin/env python3
"""
TikTok Live Recorder - Universal Launcher
Supports both CLI and GUI modes
"""
import sys
import os
import argparse

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    # Create a simple argument parser to detect if user wants GUI
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--gui", action="store_true", help="Launch GUI mode")
    parser.add_argument("--help", "-h", action="store_true", help="Show help")
    
    # Parse known args only
    known_args, remaining_args = parser.parse_known_args()
    
    if known_args.gui:
        # Launch GUI mode
        print("Launching TikTok Live Recorder GUI...")
        from gui_main import main as gui_main
        return gui_main()
    elif known_args.help and not remaining_args:
        # Show unified help
        print("""
TikTok Live Recorder v6.5
==========================

Usage:
  python launcher.py [options]              # CLI mode with options
  python launcher.py --gui                  # GUI mode
  python launcher.py --help                 # Show this help

CLI Mode Options:
  -url URL                 Record from TikTok URL
  -user USER               Record from TikTok username
  -room_id ROOM_ID         Record from TikTok room ID
  -mode MODE               Recording mode (manual, automatic)
  -automatic_interval INT  Interval for automatic mode (minutes)
  -proxy PROXY             HTTP proxy URL
  -output OUTPUT           Output directory
  -duration DURATION       Recording duration (seconds)
  -telegram                Upload to Telegram
  -no-update-check         Disable update checking

GUI Mode:
  --gui                    Launch the graphical interface

Examples:
  python launcher.py --gui
  python launcher.py -user @username -mode automatic
  python launcher.py -url "https://www.tiktok.com/@user/live"
        """)
        return 0
    else:
        # Launch CLI mode with original arguments
        print("Launching TikTok Live Recorder CLI...")
        
        # Restore original sys.argv for the CLI
        sys.argv = [sys.argv[0]] + remaining_args
        
        from main import main as cli_main
        return cli_main()

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)