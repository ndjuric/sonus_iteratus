#!/usr/bin/env python
import logging
from pathlib import Path
from typing import List


class FS:
    """
    Manages file system operations and directory structure for the application.
    """
    def __init__(self) -> None:
        self.root: Path = self.get_project_root()
        self.data_folder: Path = self.root / "data"
        self.logs_folder: Path = self.data_folder / "logs"
        self.sound_folder: Path = self.data_folder / "sound"
        self.sound_input_folder: Path = self.sound_folder / "input"
        self.sound_output_folder: Path = self.sound_folder / "output"
        self.create_directories()

    def get_project_root(self) -> Path:
        """
        Determines the project root directory.
        
        Returns:
            Path object pointing to the project root
        """
        # Assumes this file is inside the "src" directory; project root is its parent.
        return Path(__file__).resolve().parent.parent

    def create_directories(self) -> None:
        """
        Creates all necessary directories for the application if they don't exist.
        """
        required_folders = [
            self.data_folder,
            self.logs_folder,
            self.sound_folder,
            self.sound_input_folder,
            self.sound_output_folder,
        ]
        
        for folder in required_folders:
            self._create_directory(folder)
    
    def _create_directory(self, directory: Path) -> None:
        """
        Creates a single directory if it doesn't exist.
        
        Args:
            directory: Path object representing the directory to create
        """
        directory.mkdir(parents=True, exist_ok=True)
        logging.info(f"Ensured directory exists: {directory}")
        
    def get_sound_input_files(self, extension: str = "wav") -> List[Path]:
        """
        Lists all files with the given extension in the input folder.
        
        Args:
            extension: File extension to filter by (without the dot)
            
        Returns:
            List of Path objects for files with the given extension
        """
        return list(self.sound_input_folder.glob(f"*.{extension}"))