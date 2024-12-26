import subprocess
import sys
import platform
from subprocess import SubprocessError

from .logger_manager import logger


def check_distro_library():
    try:
        import distro
        return True
    except ModuleNotFoundError:
        logger.error("distro library is not installed")
        return False


def install_distro_library():
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "distro", "--break-system-packages"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=True,
        )
        logger.info("distro installed successfully\n")
    except SubprocessError as e:
        logger.error(f"Error: {e}")
        exit(1)


def check_ffmpeg_binary():
    try:
        subprocess.run(
            ["ffmpeg"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        return True
    except FileNotFoundError:
        logger.error("FFmpeg binary is not installed")
        return False


def install_ffmpeg_binary():
    try:
        logger.error('Please, install FFmpeg with this command:')
        if platform.system().lower() == "linux":

            import distro
            linux_family = distro.like()
            if linux_family == "debian":
                logger.info('sudo apt install ffmpeg')
            elif linux_family == "redhat":
                logger.info('sudo dnf install ffmpeg / sudo yum install ffmpeg')
            elif linux_family == "arch":
                logger.info('sudo pacman -S ffmpeg')
            elif linux_family == "":  # Termux
                logger.info('pkg install ffmpeg')
            else:
                logger.info(f"Distro linux not supported (family: {linux_family})")

        elif platform.system().lower() == "windows":
            logger.info('choco install ffmpeg or follow: https://phoenixnap.com/kb/ffmpeg-windows')

        elif platform.system().lower() == "darwin":
            logger.info('brew install ffmpeg')

        else:
            logger.info(f"OS not supported: {platform}")

    except Exception as e:
        logger.error(f"Error: {e}")

    exit(1)


def check_ffmpeg_library():
    try:
        import ffmpeg
        return True
    except ModuleNotFoundError:
        logger.error("ffmpeg-python library is not installed")
        return False


def install_ffmpeg_library():
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "ffmpeg-python", "--break-system-packages"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=True,
        )
        logger.info("ffmpeg-python installed successfully\n")
    except SubprocessError as e:
        logger.error(f"Error: {e}")
        exit(1)


def check_argparse_library():
    try:
        import argparse
        return True
    except ModuleNotFoundError:
        logger.error("argparse library is not installed")
        return False


def install_argparse_library():
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "argparse", "--break-system-packages"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=True,
        )
        logger.info("argparse installed successfully\n")
    except SubprocessError as e:
        logger.error(f"Error: {e}")
        exit(1)


def check_requests_library():
    try:
        import requests
        return True
    except ModuleNotFoundError:
        logger.error("requests library is not installed")
        return False


def install_requests_library():
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "requests", "--break-system-packages"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=True,
        )
        logger.info("requests installed successfully\n")
    except SubprocessError as e:
        logger.error(f"Error: {e}")
        exit(1)


def check_and_install_dependencies():
    logger.info("Checking and Installing dependencies\n")

    if not check_distro_library():
        install_distro_library()

    if not check_ffmpeg_library():
        install_ffmpeg_library()

    if not check_argparse_library():
        install_argparse_library()

    if not check_requests_library():
        install_requests_library()

    if not check_ffmpeg_binary():
        install_ffmpeg_binary()
