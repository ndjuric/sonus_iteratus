from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class ProcessResult:
    """Immutable container for audio processing results."""
    looped_audio: np.ndarray
    sr: int
    audio_path: str