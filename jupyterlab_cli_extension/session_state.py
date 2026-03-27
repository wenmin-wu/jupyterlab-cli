"""Server-side session and lock state for jupyterlab-cli."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from jupyterlab_cli_extension.lock import LockRegistry


@dataclass
class SessionInfo:
    notebook_path: str
    kernel_id: str


class SessionState:
    """Maps CLI session id -> active notebook + kernel; coordinates locks."""

    def __init__(self) -> None:
        self.locks = LockRegistry()
        self.sessions: Dict[str, SessionInfo] = {}

    def get(self, session_id: str) -> Optional[SessionInfo]:
        return self.sessions.get(session_id)

    def set_session(self, session_id: str, info: SessionInfo) -> None:
        self.sessions[session_id] = info

    def remove(self, session_id: str) -> Optional[SessionInfo]:
        return self.sessions.pop(session_id, None)

    def list_sessions(self) -> Dict[str, Any]:
        return {
            sid: {"notebook_path": info.notebook_path, "kernel_id": info.kernel_id}
            for sid, info in self.sessions.items()
        }


def get_state(handler: Any) -> SessionState:
    return handler.settings["jupyterlab_cli_state"]


def get_bridge(handler: Any) -> Any:
    return handler.settings["jupyterlab_cli_bridge"]
