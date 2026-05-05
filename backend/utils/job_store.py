import threading
from typing import Optional, Dict, Any


class JobStore:
    """Thread-safe in-memory job store."""

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def set(self, job_id: str, data: Dict[str, Any]):
        with self._lock:
            self._jobs[job_id] = data.copy()

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._jobs.get(job_id, None)

    def update(self, job_id: str, updates: Dict[str, Any]):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(updates)

    def delete(self, job_id: str):
        with self._lock:
            self._jobs.pop(job_id, None)

    def all_jobs(self) -> Dict[str, Dict]:
        with self._lock:
            return self._jobs.copy()


# Global singleton
job_store = JobStore()
