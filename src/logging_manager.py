#!/usr/bin/env python
import logging
from typing import Optional
from pathlib import Path
from compressing_rotating_file_handler import CompressingRotatingFileHandler




class LoggingManager:
    """
    Manages application logging configuration.
    """
    def __init__(self, log_file: Path) -> None:
        self.log_file = log_file
        self.handler: Optional[CompressingRotatingFileHandler] = None
        
    def setup(self, level: int = logging.INFO, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 10) -> None:
        """
        Set up logging with a rotating, compressing file handler.
        
        Args:
            level: Logging level
            max_bytes: Maximum log file size before rotation
            backup_count: Number of backup files to keep
        """
        self.handler = CompressingRotatingFileHandler(
            filename=str(self.log_file),
            mode="a",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        self.handler.setFormatter(formatter)
        
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Remove any existing handlers to prevent duplicate logs
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        root_logger.addHandler(self.handler)
        logging.info("Logging system initialized")
    
    def shutdown(self) -> None:
        """
        Properly shut down logging system
        """
        if self.handler:
            self.handler.close()
            logging.info("Logging system shutdown")