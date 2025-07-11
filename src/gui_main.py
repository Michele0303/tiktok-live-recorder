#!/usr/bin/env python3
"""
TikTok Live Recorder GUI Entry Point
"""
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# print banner
from utils.utils import banner
banner()

# check and install dependencies
from utils.dependencies import check_and_install_dependencies
check_and_install_dependencies()

from gui.main_window import main

if __name__ == "__main__":
    sys.exit(main())