#!/usr/bin/env python
"""
Audio Looper - Main Entry Point

This application finds seamless loop points in audio files and
creates extended versions by looping the best segments.
"""
import sys
from pathlib import Path

from fs import FS
from logging_manager import LoggingManager
from app import AudioLoopManager
import logging
from tui import TUI

def print_message(message: str, message_type: str) -> None:
    """
    Prints a message with a specific type indicator.

    :param message: The message to print.
    :param message_type: The type of message ('positive', 'negative', 'info').
    """
    color_map = {
        'positive': '\033[92m*',  # Green
        'negative': '\033[91m*',  # Red
        'info': '\033[94m*'       # Blue
    }
    prefix = f"\033[95m[ {color_map.get(message_type, '\033[94m*')}"
    print(f"{prefix} {message}\033[0m")


def main() -> None:
    """
    Main entry point for the application.
    
    Sets up logging and launches the application.
    """
    # Initialize file system
    fs = FS()
    
    # Configure logging
    log_file = fs.logs_folder / "app.log"
    logging_manager = LoggingManager(log_file)
    logging_manager.setup()
    
    try:
        # Launch the application
        app = AudioLoopManager()
        ui = TUI(app)
        ui.start()
    except Exception as e:
        # Log any unhandled exceptions
        import logging
        import traceback
        logging.error(f"Unhandled exception: {e}")
        logging.error(traceback.format_exc())
        print_message(f"Error: {e}", "negative")
        sys.exit(1)
    finally:
        # Ensure logging is properly shut down
        logging_manager.shutdown()


if __name__ == "__main__":
    main()