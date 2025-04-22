#!/usr/bin/env python
import curses
import logging
import signal
import sys
from pathlib import Path
from typing import Optional, Tuple, List

import librosa
import numpy as np
import argparse
from datetime import datetime
from fs import FS
from audio_processor import SirenLooper
from models import LoopCandidate, ProcessResult
from tui import TUI


class AudioLooperApp:
    """
    Main application class that orchestrates the audio looping process.
    """
    def __init__(self) -> None:
        # Register signal handler for clean exit before anything else
        signal.signal(signal.SIGINT, self._handle_exit)
        
        self.fs = FS()  # Ensure FS is initialized first
        self.args = self._parse_arguments()
        
        logging.info(f"Project root determined as: {self.fs.root}")
        
        self.audio_file: Optional[str] = self.args.audio
        self.target_duration_sec: Optional[float] = self.args.target
        self.min_loop_duration: float = self.args.min_loop_duration
        self.peak_threshold: float = self.args.peak_threshold

    def _handle_exit(self, signum, frame) -> None:
        """
        Handle clean exit on keyboard interrupt.
        """
        print("\nExiting cleanly. Goodbye!")
        sys.exit(0)

    def _parse_arguments(self) -> argparse.Namespace:
        """
        Parse command line arguments.
        
        Returns:
            Parsed arguments
        """
        parser = argparse.ArgumentParser(
            description="Create a seamlessly looped audio file.",
            epilog=f"Example usage: python app.py --audio {self.fs.sound_input_folder / 'phaser2.wav'} --target 30"
        )
        parser.add_argument(
            "--audio",
            type=str,
            default=None,
            help=f"Path to the input audio file (default: None)"
        )
        parser.add_argument(
            "--target",
            type=float,
            default=None,
            help="Target duration in seconds for the looped audio (default: None)"
        )
        parser.add_argument(
            "--min-loop-duration",
            type=float,
            default=None,
            help="Minimum loop duration in seconds. If not set, defaults to 0.1s."
        )
        parser.add_argument(
            "--peak-threshold",
            type=float,
            default=0.1,  # Default peak height threshold for loop extraction
            help="Peak height threshold for loop extraction (default: 0.1)"
        )
        return parser.parse_args()

    def _retry_loop_detection(self, looper: SirenLooper) -> bool:
        """
        Retry loop detection with progressively relaxed parameters.
        
        Args:
            looper: SirenLooper instance
            
        Returns:
            True if loop points were found, False otherwise
        """
        retries = 3
        for attempt in range(1, retries + 1):
            looper.min_loop_duration_sec /= 2
            looper.peak_height_threshold *= 0.8
            
            logging.info(
                f"Retry {attempt}/{retries} with adjusted parameters: "
                f"min_loop_duration={looper.min_loop_duration_sec:.2f}s, "
                f"threshold={looper.peak_height_threshold:.2f}"
            )
            
            try:
                looper.find_seamless_loop_points()
                if looper.loop_candidates:
                    return True
            except Exception as e:
                logging.error(f"Error during retry {attempt}: {e}")
                
        return False

    def run(self) -> None:
        # Launch the text-based UI
        ui = TUI(self)
        ui.start()