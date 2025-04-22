#!/usr/bin/env python
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np


@dataclass(frozen=True)
class ProcessResult:
    """
    Immutable container for audio processing results.
    """
    looped_audio: np.ndarray
    sr: int
    audio_path: str


@dataclass(frozen=True)
class LoopCandidate:
    """
    Represents a potential loop point in audio.
    """
    start: int
    end: int
    score: float
    
    @property
    def duration_samples(self) -> int:
        """
        Calculate loop duration in samples.
        """
        return self.end - self.start
        
    def duration_seconds(self, sr: int) -> float:
        """
        Calculate loop duration in seconds.
        
        Args:
            sr: Sample rate
            
        Returns:
            Duration in seconds
        """
        return self.duration_samples / sr