#!/usr/bin/env python
import os
import gzip
import shutil
import logging
import logging.handlers
from typing import Optional
from pathlib import Path


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