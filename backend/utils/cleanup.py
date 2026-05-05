import os
import time
import shutil
import asyncio
import threading
from pathlib import Path


def schedule_cleanup(output_dir: Path, max_age_hours: int = 2):
    """Schedule background cleanup of old output folders."""
    def _cleanup():
        while True:
            time.sleep(3600)  # Run every hour
            _clean_old_outputs(output_dir, max_age_hours)

    t = threading.Thread(target=_cleanup, daemon=True)
    t.start()


def _clean_old_outputs(output_dir: Path, max_age_hours: int):
    """Delete output folders older than max_age_hours."""
    if not output_dir.exists():
        return

    cutoff = time.time() - (max_age_hours * 3600)
    for folder in output_dir.iterdir():
        if folder.is_dir():
            mtime = folder.stat().st_mtime
            if mtime < cutoff:
                shutil.rmtree(folder, ignore_errors=True)
