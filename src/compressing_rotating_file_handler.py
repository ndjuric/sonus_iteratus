#!/usr/bin/env python
import os
import gzip
import shutil
import logging.handlers

class CompressingRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """A rotating file handler that compresses old log files."""

    def doRollover(self) -> None:
        if self.stream:
            self.stream.close()
            self.stream = None

        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = f"{self.baseFilename}.{i}.gz"
                sfn_next = f"{self.baseFilename}.{i+1}.gz"
                if os.path.exists(sfn):
                    if os.path.exists(sfn_next):
                        os.remove(sfn_next)
                    os.rename(sfn, sfn_next)

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
        files = [f for f in os.listdir(directory) if f.startswith(basename) and f.endswith(".gz")]
        files.sort(key=lambda f: os.path.getmtime(os.path.join(directory, f)))
        while len(files) > self.backupCount:
            oldest = files.pop(0)
            os.remove(os.path.join(directory, oldest))