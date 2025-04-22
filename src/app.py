#!/usr/bin/env python
import argparse
import curses
import logging
import signal
import sys
from pathlib import Path
from time import sleep
from typing import Optional, Tuple, List

import librosa
import numpy as np
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table

from fs import FS
from audio_processor import SirenLooper
from models import LoopCandidate, ProcessResult


class UserInterface:
    """
    Handles all user interface operations, separating UI concerns from business logic.
    """
    def __init__(self) -> None:
        self.console = Console()
        
    def display_file_selection_table(self, files: List[Path]) -> None:
        """
        Display a table of available audio files.
        
        Args:
            files: List of Path objects representing available files
        """
        table = Table(title="Available Audio Files")
        table.add_column("Index", justify="right", style="cyan", no_wrap=True)
        table.add_column("File Name", style="magenta")

        for idx, file in enumerate(files, start=1):
            table.add_row(str(idx), file.name)

        self.console.print(table)
        
    def get_file_selection(self, max_files: int) -> int:
        """
        Get user selection from available files.
        
        Args:
            max_files: Maximum number of files available
            
        Returns:
            Index of selected file (1-based)
        """
        while True:
            try:
                choice = int(self.console.input("[bold green]Select a file by index: [/bold green]"))
                if 1 <= choice <= max_files:
                    return choice
                
                self.console.print("[bold red]Invalid choice. Try again.[/bold red]")
            except ValueError:
                self.console.print("[bold red]Please enter a valid number.[/bold red]")
                
    def get_target_duration(self, audio_duration: float) -> float:
        """
        Get target duration from the user.
        
        Args:
            audio_duration: Duration of the original audio in seconds
            
        Returns:
            Target duration in seconds
        """
        while True:
            try:
                target_duration = float(self.console.input("[bold green]Enter target duration (seconds): [/bold green]"))
                if target_duration <= 0:
                    self.console.print("[bold red]Duration must be positive. Try again.[/bold red]")
                    continue
                    
                if target_duration < audio_duration:
                    self.console.print(
                        f"[bold red]Target duration ({target_duration}s) is shorter than the audio length "
                        f"({audio_duration:.2f}s). Try again.[/bold red]"
                    )
                    continue
                    
                return target_duration
            except ValueError:
                self.console.print("[bold red]Please enter a valid number.[/bold red]")
                
    def show_file_selected(self, file: Path) -> None:
        """
        Display the selected file.
        
        Args:
            file: Path to the selected file
        """
        self.console.print(f"[bold blue]You selected:[/bold blue] {file}")
        
    def display_error(self, message: str) -> None:
        """
        Display an error message.
        
        Args:
            message: Error message to display
        """
        self.console.print(f"[bold red]Error: {message}[/bold red]")
        
    def display_info(self, message: str) -> None:
        """
        Display an informational message.
        
        Args:
            message: Info message to display
        """
        self.console.print(f"[*] {message}")
        
    def display_success(self, message: str) -> None:
        """
        Display a success message.
        
        Args:
            message: Success message to display
        """
        self.console.print(f"[bold green]{message}[/bold green]")
        
    def run_with_progress(self, description: str, action_func) -> any:
        """
        Run a function with a progress indicator.
        
        Args:
            description: Description of the action
            action_func: Function to execute
            
        Returns:
            Result of action_func
        """
        with Progress() as progress:
            task = progress.add_task(f"[cyan]{description}", total=100)
            
            # Start task
            for i in range(100):
                sleep(0.01)  # For visualization only
                progress.update(task, advance=1)
                
            # Execute the actual function at any point
            result = action_func()
            
            return result


class AudioLooperApp:
    """
    Main application class that orchestrates the audio looping process.
    """
    def __init__(self) -> None:
        # Register signal handler for clean exit before anything else
        signal.signal(signal.SIGINT, self._handle_exit)
        
        self.fs = FS()  # Ensure FS is initialized first
        self.ui = UserInterface()  
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
        self.ui.console.print("\n[bold yellow]Exiting cleanly. Goodbye![/bold yellow]")
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
            default=None,  # Dynamically calculated later
            help="Minimum loop duration in seconds. Defaults to the duration of the audio file."
        )
        parser.add_argument(
            "--peak-threshold",
            type=float,
            default=0.5,  # Adjusted for better default behavior
            help="Peak height threshold for loop extraction (default: 0.5)"
        )
        return parser.parse_args()

    def _interactive_mode(self) -> Tuple[Optional[Path], Optional[float]]:
        """
        Run the application in interactive mode.
        
        Returns:
            Tuple of (selected_file, target_duration) or (None, None) if failed
        """
        files = self.fs.get_sound_input_files()

        if not files:
            self.ui.display_error(f"No .wav files found in {self.fs.sound_input_folder}")
            self.ui.display_info(f"Please add .wav files to the folder and re-run the program.")
            return None, None

        # Display file selection table and get user's choice
        self.ui.display_file_selection_table(files)
        choice = self.ui.get_file_selection(len(files))
        selected_file = files[choice - 1]
        self.ui.show_file_selected(selected_file)

        # Analyze file to get its duration
        try:
            def get_audio_duration():
                y, sr = librosa.load(selected_file, sr=None)
                return len(y) / sr
            
            audio_duration = self.ui.run_with_progress("Analyzing audio file...", get_audio_duration)
            self.ui.display_info(f"Audio length is {audio_duration:.2f} seconds.")
            
            # Get target duration from user
            target_duration = self.ui.get_target_duration(audio_duration)
            return selected_file, target_duration
            
        except Exception as e:
            self.ui.display_error(f"Failed to analyze audio file: {e}")
            return None, None

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
            
            self.ui.display_info(
                f"Retry {attempt}/{retries} with adjusted parameters: "
                f"min_loop_duration={looper.min_loop_duration_sec:.2f}s, "
                f"threshold={looper.peak_height_threshold:.2f}"
            )
            
            try:
                looper.find_seamless_loop_points()
                if looper.loop_candidates:
                    return True
            except Exception as e:
                self.ui.display_error(f"Error during retry {attempt}: {e}")
                
        return False

    def _manual_loop_selection(self, audio_file: str) -> None:
        """
        Removed manual loop selection. Instead, display a failure message.
        """
        self.ui.display_error("No suitable loop points found. 😢")
        self.ui.display_info("Please try again with a different file or adjust parameters.")

    def run(self) -> None:
        """
        Main method to run the application.
        """
        # Get input file either from args or interactive mode
        file_path = None
        if not self.audio_file:
            file_path, _ = self._interactive_mode()
            if not file_path:
                return
            self.audio_file = file_path.name

        # Validate input file is a WAV file
        def check_file_format():
            if not self.audio_file.lower().endswith('.wav'):
                raise ValueError(f"{self.audio_file} is not a WAV file.")
            return True

        self.ui.run_with_progress("Checking file format...", check_file_format)
        self.ui.console.print("[purple][green *] {self.audio_file} is a valid WAV file!")

        # Create the SirenLooper instance
        looper = SirenLooper(
            self.audio_file,
            fs=self.fs,
            min_loop_duration_sec=self.min_loop_duration if self.min_loop_duration else 0.1,
            peak_height_threshold=self.peak_threshold
        )

        # Find loop points
        def find_loop_points():
            try:
                return looper.find_seamless_loop_points()
            except Exception as e:
                logging.error(f"Error finding loop points: {e}")
                raise

        self.ui.run_with_progress("[purple][blue *] Looking for seamless loop points...", find_loop_points)

        # Check if loop points were found
        if not looper.loop_candidates:
            self.ui.console.print("[purple][red *] No loop points found. Trying with relaxed parameters...")
            if not self._retry_loop_detection(looper):
                self.ui.console.print("[purple][red *] Failed to find loop points even with relaxed parameters.")
                retry = self.ui.console.input("[purple][blue *] Would you like us to repeat the entire file? (y/n): ")
                if retry.lower() != 'y':
                    return

        # Ask for target duration
        target_duration = self.ui.console.input("[purple][blue *] Enter target duration (seconds): ")
        try:
            self.target_duration_sec = float(target_duration)
        except ValueError:
            self.ui.console.print("[purple][red *] Invalid duration entered. Exiting.")
            return

        # Process and save the looped audio
        def process_and_save():
            return looper.process_and_save(self.target_duration_sec)

        result = self.ui.run_with_progress("[purple][blue *] Processing and saving looped audio...", process_and_save)
        self.ui.console.print(f"[purple][green *] Looped file saved: {result.audio_path}")