"""In-memory lock registry: one notebook path can be locked by one session at a time."""

from __future__ import annotations

from typing import Dict, Optional


class LockRegistry:
    def __init__(self) -> None:
        self._locks: Dict[str, str] = {}

    def holder(self, notebook_path: str) -> Optional[str]:
        return self._locks.get(notebook_path)

    def acquire(self, notebook_path: str, session_id: str, force: bool) -> bool:
        current = self._locks.get(notebook_path)
        if current is None:
            self._locks[notebook_path] = session_id
            return True
        if current == session_id:
            return True
        if force:
            self._locks[notebook_path] = session_id
            return True
        return False

    def release_path(self, notebook_path: str, session_id: str) -> bool:
        if self._locks.get(notebook_path) != session_id:
            return False
        del self._locks[notebook_path]
        return True

    def release_session(self, session_id: str) -> list[str]:
        released: list[str] = []
        for path, sid in list(self._locks.items()):
            if sid == session_id:
                del self._locks[path]
                released.append(path)
        return released
