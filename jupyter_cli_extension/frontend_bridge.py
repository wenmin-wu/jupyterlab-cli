"""Broadcast notebook / cell events to connected JupyterLab WebSocket clients."""

from __future__ import annotations

import json
import logging
from typing import Any, List

logger = logging.getLogger(__name__)


class FrontendBridge:
    def __init__(self) -> None:
        self._connections: List[Any] = []

    def register(self, ws: Any) -> None:
        self._connections.append(ws)
        logger.debug("jupyter-cli WS client connected (%s total)", len(self._connections))

    def unregister(self, ws: Any) -> None:
        try:
            self._connections.remove(ws)
        except ValueError:
            pass
        logger.debug("jupyter-cli WS client disconnected (%s total)", len(self._connections))

    def broadcast(self, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload)
        dead: List[Any] = []
        for ws in self._connections:
            try:
                ws.write_message(raw)
            except Exception as e:  # noqa: BLE001
                logger.debug("WS send failed: %s", e)
                dead.append(ws)
        for ws in dead:
            self.unregister(ws)
