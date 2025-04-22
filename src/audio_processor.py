#!/usr/bin/env python
import os
import logging
from pathlib import Path
from typing import List, Optional, Tuple

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import find_peaks

from fs import FS
from models import ProcessResult, LoopCandidate


class SirenLooper:
    """
    Class responsible for audio processing operations including:
    - Finding seamless loop points in audio files
    - Creating looped audio segments
    - Saving processed audio
    """
    def __init__(self, audio_file: str, fs: FS, min_loop_duration_sec: float = 0.1, peak_height_threshold: float = 0.3) -> None:
        """
        Initialize the SirenLooper with an audio file.
        
        Args:
            audio_file: Name of the audio file (not full path)
            fs: File system manager
            min_loop_duration_sec: Minimum acceptable loop duration in seconds
            peak_height_threshold: Threshold for peak detection
        """
        self.fs = fs
        self.audio_file: str = str(self.fs.sound_input_folder / audio_file)
        self.min_loop_duration_sec: float = min_loop_duration_sec
        self.peak_height_threshold: float = peak_height_threshold
        self.y: Optional[np.ndarray] = None
        self.sr: Optional[int] = None
        self.loop_candidates: List[LoopCandidate] = []
        self._load_audio()

    def _load_audio(self) -> None:
        """
        Load audio file into memory.
        
        Raises:
            RuntimeError: If file not found or loading fails
        """
        if not os.path.exists(self.audio_file):
            raise RuntimeError(f"Audio file not found: {self.audio_file}")
        
        try:
            self.y, self.sr = librosa.load(self.audio_file)
        except Exception as e:
            raise RuntimeError(f"Error loading audio file: {e}")

    def find_seamless_loop_points(self, num_candidates: int = 5) -> List[LoopCandidate]:
        """
        Find potential seamless loop points in the audio.
        
        Args:
            num_candidates: Maximum number of candidates to return
            
        Returns:
            List of LoopCandidate objects, sorted by quality score
            
        Raises:
            ValueError: If audio is not loaded
        """
        if self.y is None or self.sr is None:
            raise ValueError("Audio not loaded")
            
        min_loop_samples: int = int(self.min_loop_duration_sec * self.sr)
        hop_length: int = 512
        # Ensure distance parameter for peak detection is at least 1
        distance = max(min_loop_samples // hop_length, 1)
        
        # Extract chroma features
        chroma: np.ndarray = librosa.feature.chroma_cqt(y=self.y, sr=self.sr, hop_length=hop_length)
        
        # Build similarity matrix
        ssm: np.ndarray = librosa.segment.recurrence_matrix(chroma, mode='affinity', sym=True)
        ssm_enhanced: np.ndarray = librosa.segment.path_enhance(ssm, 5)
        
        # Smooth the similarity matrix
        ssm_smooth: np.ndarray = np.mean(
            np.lib.stride_tricks.sliding_window_view(ssm_enhanced, (5, 5)), axis=(2, 3)
        )
        
        # Find peaks in the similarity matrix
        peaks, _ = find_peaks(
            ssm_smooth.flatten(), height=self.peak_height_threshold, distance=distance
        )
        
        # Convert peak indices to coordinates
        peak_coords: np.ndarray = np.array(np.unravel_index(peaks, ssm.shape)).T
        
        # Generate loop candidates
        loop_candidates: List[LoopCandidate] = []
        for start_frame, end_frame in peak_coords:
            if end_frame - start_frame < min_loop_samples // hop_length:
                continue
                
            start_sample: int = start_frame * hop_length
            end_sample: int = end_frame * hop_length
            score: float = ssm[start_frame, end_frame]
            
            loop_candidates.append(LoopCandidate(start=start_sample, end=end_sample, score=score))

        # Sort by score (highest first) and keep top candidates
        loop_candidates.sort(key=lambda x: x.score, reverse=True)
        self.loop_candidates = loop_candidates[:num_candidates]
        
        return self.loop_candidates

    def create_looped_audio(self, loop_candidate: LoopCandidate, target_duration_sec: float) -> np.ndarray:
        """
        Create a looped audio segment of the specified duration.
        
        Args:
            loop_candidate: The LoopCandidate to use for looping
            target_duration_sec: Target duration in seconds
            
        Returns:
            Numpy array containing the looped audio
            
        Raises:
            ValueError: If audio is not loaded
        """
        if self.y is None or self.sr is None:
            raise ValueError("Audio not loaded")
            
        loop_segment: np.ndarray = self.y[loop_candidate.start:loop_candidate.end]
        loop_duration_sec: float = loop_candidate.duration_seconds(self.sr)
        
        num_reps: int = int(target_duration_sec // loop_duration_sec)
        if num_reps == 0:
            num_reps = 1
            logging.warning("Target duration is shorter than the best loop. Using one repetition.")
            
        logging.info(f"Loop duration: {loop_duration_sec:.2f} seconds, repeating {num_reps} times.")
        
        looped_audio: np.ndarray = np.tile(loop_segment, num_reps)
        return looped_audio

    def get_best_loop(self) -> Optional[LoopCandidate]:
        """
        Get the best loop candidate (highest score).
        
        Returns:
            Best LoopCandidate or None if no candidates available
        """
        if not self.loop_candidates:
            return None
        return self.loop_candidates[0]

    def process_and_save(self, target_duration_sec: float, output_file: Optional[str] = None) -> ProcessResult:
        """
        Process audio to create a seamless loop and save to file.
        
        Args:
            target_duration_sec: Target duration in seconds
            output_file: Optional filename, will be auto-generated if None
            
        Returns:
            ProcessResult object with processing results
            
        Raises:
            RuntimeError: If no suitable loop points found
        """
        if not self.loop_candidates:
            self.find_seamless_loop_points()
            
        best_loop: Optional[LoopCandidate] = self.get_best_loop()
        if best_loop is None:
            raise RuntimeError("No suitable loop points found.")
            
        looped_audio: np.ndarray = self.create_looped_audio(best_loop, target_duration_sec)
        
        if output_file is None:
            base_name: str = os.path.splitext(os.path.basename(self.audio_file))[0]
            output_file = f"{base_name}_looped_{int(target_duration_sec)}s.wav"
            
        output_path = self.fs.sound_output_folder / output_file
        
        if self.sr is None:
            raise RuntimeError("Sample rate not available")
            
        sf.write(str(output_path), looped_audio, self.sr)
        logging.info(f"Looped audio saved to: {output_path}")
        
        return ProcessResult(looped_audio=looped_audio, sr=self.sr, audio_path=str(output_path))