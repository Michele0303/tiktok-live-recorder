import subprocess
import sys
import platform
from subprocess import SubprocessError

from .logger_manager import logger
from .utils import is_linux


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
        logger.error("Please, install FFmpeg with this command:")
        if platform.system().lower() == "linux":
            import distro

            linux_family = distro.like()
            if linux_family == "debian":
                logger.info("sudo apt install ffmpeg")
            elif linux_family == "redhat":
                logger.info("sudo dnf install ffmpeg / sudo yum install ffmpeg")
            elif linux_family == "arch":
                logger.info("sudo pacman -S ffmpeg")
            elif linux_family == "":  # Termux
                logger.info("pkg install ffmpeg")
            else:
                logger.info(f"Distro linux not supported (family: {linux_family})")

        elif platform.system().lower() == "windows":
            logger.info(
                "choco install ffmpeg or follow: https://phoenixnap.com/kb/ffmpeg-windows"
            )

        elif platform.system().lower() == "darwin":
            logger.info("brew install ffmpeg")

        else:
            logger.info(f"OS not supported: {platform}")

    except Exception as e:
        logger.error(f"Error: {e}")

    exit(1)


def check_distro_library():
    try:
        import distro

        _ = distro  # to avoid linting issues

        return True
    except ModuleNotFoundError:
        logger.error("distro library is not installed")
        return False


def check_ffmpeg_library():
    try:
        import ffmpeg

        _ = ffmpeg  # to avoid linting issues

        return True
    except ModuleNotFoundError:
        logger.error("ffmpeg-python library is not installed")
        return False


def check_argparse_library():
    try:
        import argparse

        _ = argparse  # to avoid linting issues

        return True
    except ModuleNotFoundError:
        logger.error("argparse library is not installed")
        return False


def check_curl_cffi_library():
    try:
        from .utils import is_termux

        if is_termux():
            return True

        import curl_cffi

        _ = curl_cffi  # to avoid linting issues

        return True
    except ModuleNotFoundError:
        logger.error("curl_cffi library is not installed")
        return False


def check_requests_library():
    try:
        import requests

        _ = requests  # to avoid linting issues

        return True
    except ModuleNotFoundError:
        logger.error("requests library is not installed")
        return False


def check_telethon_library():
    try:
        import telethon

        _ = telethon  # to avoid linting issues

        return True
    except ModuleNotFoundError:
        logger.error("telethon library is not installed")
        return False


def install_requirements():
    try:
        print()
        logger.error("Installing requirements...\n")

        cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        if is_linux():
            cmd.append("--break-system-packages")

        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=True,
        )
        logger.info("Requirements installed successfully\n")
    except SubprocessError as e:
        logger.error(f"Error: {e}")
        exit(1)


def check_and_install_dependencies():
    logger.info("Checking and Installing dependencies...")

    dependencies = [
        check_distro_library(),
        check_ffmpeg_library(),
        check_argparse_library(),
        check_curl_cffi_library(),
        check_requests_library(),
        check_telethon_library(),
        check_ffmpeg_binary(),
    ]

    if False in dependencies:
        install_requirements()

    if not check_ffmpeg_binary():
        install_ffmpeg_binary()
