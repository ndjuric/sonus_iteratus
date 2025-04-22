#!/usr/bin/env python
import os
import logging
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple
import gzip
import shutil
import signal
import sys

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import find_peaks
import logging.handlers
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel
from rich.live import Live
from time import sleep
import curses


class FS:
    def __init__(self) -> None:
        self.root: Path = self.get_project_root()
        self.data_folder: Path = self.root / "data"
        self.logs_folder: Path = self.data_folder / "logs"
        self.sound_folder: Path = self.data_folder / "sound"
        self.sound_input_folder: Path = self.sound_folder / "input"
        self.sound_output_folder: Path = self.sound_folder / "output"
        self.create_directories()

    def get_project_root(self) -> Path:
        # Assumes this file is inside the "src" directory; project root is its parent.
        return Path(__file__).resolve().parent.parent

    def create_directories(self) -> None:
        for folder in [
            self.data_folder,
            self.logs_folder,
            self.sound_folder,
            self.sound_input_folder,
            self.sound_output_folder,
        ]:
            folder.mkdir(parents=True, exist_ok=True)
            logger = logging.getLogger(__name__)
            logger.info(f"Ensured directory exists: {folder}")


@dataclass(frozen=True)
class ProcessResult:
    looped_audio: np.ndarray
    sr: int
    audio_path: str


class SirenLooper:
    def __init__(self, audio_file: str, fs: FS, min_loop_duration_sec: float = 0.1, peak_height_threshold: float = 0.3) -> None:
        self.fs = fs
        self.audio_file: str = str(self.fs.sound_input_folder / audio_file)
        self.min_loop_duration_sec: float = min_loop_duration_sec
        self.peak_height_threshold: float = peak_height_threshold
        self.y: Optional[np.ndarray] = None
        self.sr: Optional[int] = None
        self.loop_points: List[Tuple[int, int]] = []
        self._load_audio()

    def _load_audio(self) -> None:
        if not os.path.exists(self.audio_file):
            raise RuntimeError(f"Audio file not found: {self.audio_file}")
        try:
            self.y, self.sr = librosa.load(self.audio_file)
        except Exception as e:
            raise RuntimeError(f"Error loading audio file: {e}")

    def find_seamless_loop_points(self, num_candidates: int = 5) -> List[Tuple[int, int, float]]:
        if self.y is None or self.sr is None:
            raise ValueError("Audio not loaded")
        min_loop_samples: int = int(self.min_loop_duration_sec * self.sr)
        hop_length: int = 512
        chroma: np.ndarray = librosa.feature.chroma_cqt(y=self.y, sr=self.sr, hop_length=hop_length)
        ssm: np.ndarray = librosa.segment.recurrence_matrix(chroma, mode='affinity', sym=True)
        ssm_enhanced: np.ndarray = librosa.segment.path_enhance(ssm, 5)
        ssm_smooth: np.ndarray = np.mean(
            np.lib.stride_tricks.sliding_window_view(ssm_enhanced, (5, 5)), axis=(2, 3)
        )
        peaks, _ = find_peaks(
            ssm_smooth.flatten(), height=self.peak_height_threshold, distance=min_loop_samples // hop_length
        )
        peak_coords: np.ndarray = np.array(np.unravel_index(peaks, ssm.shape)).T
        loop_candidates: List[Tuple[int, int, float]] = []
        for start_frame, end_frame in peak_coords:
            if end_frame - start_frame >= min_loop_samples // hop_length:
                start_sample: int = start_frame * hop_length
                end_sample: int = end_frame * hop_length
                score: float = ssm[start_frame, end_frame]
                loop_candidates.append((start_sample, end_sample, score))
        loop_candidates.sort(key=lambda x: x[2], reverse=True)
        self.loop_points = [(start, end) for start, end, _ in loop_candidates[:num_candidates]]
        return loop_candidates[:num_candidates]

    def create_looped_audio(self, loop_start: int, loop_end: int, target_duration_sec: float) -> np.ndarray:
        if self.y is None or self.sr is None:
            raise ValueError("Audio not loaded")
        loop_segment: np.ndarray = self.y[loop_start:loop_end]
        loop_duration_sec: float = (loop_end - loop_start) / self.sr
        num_reps: int = int(target_duration_sec // loop_duration_sec)
        if num_reps == 0:
            num_reps = 1
            logging.warning("Target duration is shorter than the best loop. Using one repetition.")
        logging.info(f"Loop duration: {loop_duration_sec:.2f} seconds, repeating {num_reps} times.")
        looped_audio: np.ndarray = np.tile(loop_segment, num_reps)
        return looped_audio

    def get_best_loop(self) -> Optional[Tuple[int, int]]:
        if self.loop_points:
            return self.loop_points[0]
        return None

    def process_and_save(self, target_duration_sec: float, output_file: Optional[str] = None) -> ProcessResult:
        if not self.loop_points:
            self.find_seamless_loop_points()
        best_loop: Optional[Tuple[int, int]] = self.get_best_loop()
        if best_loop is None:
            raise RuntimeError("No suitable loop points found.")
        best_start, best_end = best_loop
        looped_audio: np.ndarray = self.create_looped_audio(best_start, best_end, target_duration_sec)
        if output_file is None:
            base_name: str = os.path.splitext(os.path.basename(self.audio_file))[0]
            output_file = f"{base_name}_looped_{int(target_duration_sec)}s.wav"
        output_path = self.fs.sound_output_folder / output_file
        sf.write(output_path, looped_audio, self.sr)  # type: ignore
        logging.info(f"Looped audio saved to: {output_path}")
        return ProcessResult(looped_audio=looped_audio, sr=self.sr, audio_path=str(output_path))  # type: ignore


class AudioLooperApp:
    def __init__(self) -> None:
        self.fs = FS()  # Ensure FS is initialized first
        self.args = self._parse_arguments()
        logging.info(f"Project root determined as: {self.fs.root}")
        self.audio_file: Optional[str] = self.args.audio
        self.target_duration_sec: Optional[float] = self.args.target
        self.min_loop_duration: float = self.args.min_loop_duration
        self.peak_threshold: float = self.args.peak_threshold
        self.console = Console()

        # Register signal handler for clean exit
        signal.signal(signal.SIGINT, self._handle_exit)

    def _handle_exit(self, signum, frame):
        self.console.print("\n[bold yellow]Exiting cleanly. Goodbye![/bold yellow]")
        sys.exit(0)

    def _parse_arguments(self):
        parser = argparse.ArgumentParser(
            description="Create a seamlessly looped audio file.",
            epilog=f"Example usage: python frud.py --audio {self.fs.sound_input_folder / 'phaser2.wav'} --target 30"
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

    def _interactive_mode(self):
        input_folder = self.fs.sound_input_folder
        files = list(input_folder.glob("*.wav"))

        if not files:
            self.console.print(f"[bold red]No .wav files found in {input_folder}.[/bold red]")
            self.console.print(f"Please add .wav files to the folder and re-run the program.")
            return None, None

        table = Table(title="Available Audio Files")
        table.add_column("Index", justify="right", style="cyan", no_wrap=True)
        table.add_column("File Name", style="magenta")

        for idx, file in enumerate(files, start=1):
            table.add_row(str(idx), file.name)

        self.console.print(table)

        while True:
            try:
                choice = int(self.console.input("[bold green]Select a file by index: [/bold green]"))
                if 1 <= choice <= len(files):
                    selected_file = files[choice - 1]
                    break
                else:
                    self.console.print("[bold red]Invalid choice. Try again.[/bold red]")
            except ValueError:
                self.console.print("[bold red]Please enter a valid number.[/bold red]")

        self.console.print(f"[bold blue]You selected:[/bold blue] {selected_file}")

        # Perform analysis before asking for target duration
        log_panel = Panel("[bold cyan]Log Panel[/bold cyan]", title="Logs", border_style="blue")
        progress_panel = Panel("[bold cyan]Progress Panel[/bold cyan]", title="Progress", border_style="green")

        with Live(Panel.fit("[bold cyan]Analyzing file...[/bold cyan]", title="Analysis", border_style="magenta"), refresh_per_second=10) as live:
            progress = Progress()
            task = progress.add_task("[cyan]Analyzing file...", total=100)

            # Step 2.1: Check if the file is a .wav file
            progress.update(task, advance=20, description="[cyan]Checking file format...")
            sleep(0.5)  # Simulate progress
            if not selected_file.name.endswith(".wav"):
                self.console.print(f"[bold red]Error: {selected_file} is not a .wav file.[/bold red]")
                return None, None

            # Step 2.2: Determine the length of the recording
            progress.update(task, advance=40, description="[cyan]Determining audio length...")
            sleep(0.5)  # Simulate progress
            y, sr = librosa.load(selected_file, sr=None)
            audio_duration = len(y) / sr
            live.update(Panel(f"[bold blue]Audio length:[/bold blue] {audio_duration:.2f} seconds", title="Logs", border_style="blue"))

        target_duration = None
        while target_duration is None:
            try:
                target_duration = float(self.console.input("[bold green]Enter target duration (seconds): [/bold green]"))
                if target_duration <= 0:
                    self.console.print("[bold red]Duration must be positive. Try again.[/bold red]")
                    target_duration = None
                elif target_duration < audio_duration:
                    self.console.print(f"[bold red]Target duration ({target_duration}s) is shorter than the audio length ({audio_duration:.2f}s). Try again.[/bold red]")
                    target_duration = None
            except ValueError:
                self.console.print("[bold red]Please enter a valid number.[/bold red]")

        return selected_file, target_duration

    def _retry_loop_detection(self, looper):
        """Retry loop detection with progressively relaxed parameters."""
        retries = 3
        for attempt in range(1, retries + 1):
            looper.min_loop_duration_sec /= 2
            looper.peak_height_threshold *= 0.8
            self.console.print(
                f"[bold yellow]Retry {attempt}/{retries} with min_loop_duration_sec={looper.min_loop_duration_sec:.2f}, peak_height_threshold={looper.peak_height_threshold:.2f}[/bold yellow]"
            )
            try:
                looper.find_seamless_loop_points()
                if looper.loop_points:
                    return True
            except Exception as e:
                self.console.print(f"[bold red]Error during retry {attempt}: {e}[/bold red]")
        return False

    def _manual_loop_selection(self, audio_file):
        """Launch a TUI for manual loop selection."""
        def draw_waveform(stdscr):
            curses.curs_set(0)
            stdscr.clear()
            stdscr.addstr(0, 0, "[Waveform Visualization - Manual Loop Selection]")
            stdscr.addstr(2, 0, "Use TAB to switch sides, ARROWS to adjust, ALT+ARROWS to slide, ENTER to finish.")
            stdscr.addstr(3, 0, "Press Q to quit.")

            # Simulate waveform visualization (replace with actual waveform rendering)
            waveform = "".join(["." if i % 2 == 0 else " " for i in range(100)])
            stdscr.addstr(5, 0, waveform)

            # Simulate a selection window
            left, right = 20, 80
            while True:
                stdscr.addstr(6, 0, " " * 100)  # Clear previous selection
                stdscr.addstr(6, left, "[", curses.A_REVERSE)
                stdscr.addstr(6, left + 1, "=" * (right - left - 1))
                stdscr.addstr(6, right, "]", curses.A_REVERSE)
                stdscr.refresh()

                key = stdscr.getch()
                if key == ord("q"):
                    break
                elif key == curses.KEY_LEFT and left > 0:
                    left -= 1
                elif key == curses.KEY_RIGHT and right < 100:
                    right += 1
                elif key == 9:  # TAB key
                    # Switch sides (not implemented in this mockup)
                    pass
                elif key == 10:  # ENTER key
                    # Finish selection
                    break

        curses.wrapper(draw_waveform)

    def run(self) -> None:
        if not self.audio_file or not self.target_duration_sec:
            self.audio_file, self.target_duration_sec = self._interactive_mode()
            if not self.audio_file or not self.target_duration_sec:
                return

        with Progress() as progress:
            progress_check_format = progress.add_task("[cyan]Checking file format...", total=100)
            for i in range(100):
                sleep(0.01)
                progress.update(progress_check_format, advance=1)
            self.console.print(f"[*] {self.audio_file} is a valid WAV file! :smiley:")

            progress_loading_audio = progress.add_task("[cyan]Loading audio...", total=100)
            for i in range(100):
                sleep(0.01)
                progress.update(progress_loading_audio, advance=1)
            self.console.print("[*] Audio loaded successfully!")

            y, sr = librosa.load(self.audio_file, sr=None)
            audio_duration = len(y) / sr

            progress_determ_length = progress.add_task("[cyan]Determining audio length...", total=100)
            for i in range(100):
                sleep(0.01)
                progress.update(progress_determ_length, advance=1)
            self.console.print(f"[*] Duration is {audio_duration:.2f} seconds.")

            looper = SirenLooper(
                self.audio_file,
                fs=self.fs,
                min_loop_duration_sec=self.min_loop_duration,
                peak_height_threshold=self.peak_threshold
            )

            progress_finding_loops = progress.add_task("[cyan]Finding seamless loop points...", total=100)
            for i in range(100):
                sleep(0.01)
                progress.update(progress_finding_loops, advance=1)
            self.console.print("[*] Loop points search complete.")

            try:
                looper.find_seamless_loop_points()
            except Exception as e:
                self.console.print(f"[bold red]Error finding loop points: {e}[/bold red]")
                return

            if not looper.loop_points:
                if not self._retry_loop_detection(looper):
                    self.console.print("[bold red]No suitable loop points found even after retrying.[/bold red]")
                    self._manual_loop_selection(self.audio_file)
                    return

            progress_process_save = progress.add_task("[cyan]Processing and saving looped audio...", total=100)
            for i in range(100):
                sleep(0.01)
                progress.update(progress_process_save, advance=1)
            result = looper.process_and_save(self.target_duration_sec)
            self.console.print(f"[*] Looped file saved: {result.audio_path}")


class CompressingRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    A rotating file handler that compresses old log files.
    Rotates at maxBytes and keeps backupCount compressed files.
    """
    def doRollover(self) -> None:
        if self.stream:
            self.stream.close()
            self.stream = None

        # Rotate the files.
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = f"{self.baseFilename}.{i}.gz"
                sfn_next = f"{self.baseFilename}.{i+1}.gz"
                if os.path.exists(sfn):
                    if os.path.exists(sfn_next):
                        os.remove(sfn_next)
                    os.rename(sfn, sfn_next)

            # Rotate the current log file.
            dfn = f"{self.baseFilename}.1"
            if os.path.exists(dfn):
                os.remove(dfn)
            os.rename(self.baseFilename, dfn)
            self.compress_log(dfn)

        self.mode = "w"
        self.stream = self._open()
        self.cleanup_old_logs()

    def compress_log(self, file_path: str) -> None:
        compressed_path = file_path + ".gz"
        with open(file_path, "rb") as f_in, gzip.open(compressed_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(file_path)

    def cleanup_old_logs(self) -> None:
        directory = os.path.dirname(self.baseFilename)
        basename = os.path.basename(self.baseFilename)
        # Find all compressed log files matching the basename.
        files = [f for f in os.listdir(directory) if f.startswith(basename) and f.endswith(".gz")]
        files.sort(key=lambda f: os.path.getmtime(os.path.join(directory, f)))
        # Remove the oldest files if backups exceed backupCount.
        while len(files) > self.backupCount:
            oldest = files.pop(0)
            os.remove(os.path.join(directory, oldest))


def setup_logging() -> None:
    # Create a temporary FS to get the logs directory.
    fs = FS()
    log_file = fs.logs_folder / "app.log"
    handler = CompressingRotatingFileHandler(
        filename=str(log_file),
        mode="a",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10,
        encoding="utf-8"
    )
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)


def main() -> None:
    setup_logging()
    app = AudioLooperApp()
    app.run()


if __name__ == "__main__":
    main()