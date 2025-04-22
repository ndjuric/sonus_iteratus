from dataclasses import dataclass

@dataclass(frozen=True)
class LoopCandidate:
    """Represents a potential loop point in audio."""
    start: int
    end: int
    score: float

    @property
    def duration_samples(self) -> int:
        """Calculate loop duration in samples."""
        return self.end - self.start

    def duration_seconds(self, sr: int) -> float:
        """Calculate loop duration in seconds."""
        return self.duration_samples / sr