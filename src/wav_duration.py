#!/usr/bin/env python
import librosa
import sys
import os

def get_wav_duration(file_path):
    """Gets the duration of a WAV file in seconds."""
    try:
        y, sr = librosa.load(file_path, sr=None)  # Load with original sample rate
        duration = librosa.get_duration(y=y, sr=sr)
        return duration
    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python wav_duration.py <wav_file1> [<wav_file2> ...]")
        sys.exit(1)

    for file_path in sys.argv[1:]:
      if not os.path.exists(file_path):
        print(f"Error processing {file_path}: File does not exist", file=sys.stderr)
        continue

      if not file_path.lower().endswith(".wav"):
          print(f"Error: {file_path} is not a .wav file.", file=sys.stderr)
          continue
      duration = get_wav_duration(file_path)
      if duration is not None:
          print(f"{file_path}: {duration:.3f} seconds")



if __name__ == "__main__":
    main()