"""Jupyter Server ExtensionApp: REST API + WebSocket bridge for jupyterlab-cli."""

from __future__ import annotations

import logging

from jupyter_server.extension.application import ExtensionApp

from jupyterlab_cli_extension.frontend_bridge import FrontendBridge
from jupyterlab_cli_extension.routes import (
    BridgeWebSocketHandler,
    CellItemHandler,
    CellsAddHandler,
    ClipboardImageHandler,
    ExecuteCellHandler,
    ExecuteCodeHandler,
    FilesListHandler,
    HealthHandler,
    KernelsListHandler,
    NotebookReadHandler,
    RestartKernelHandler,
    SessionDeleteHandler,
    SessionsHandler,
)
from jupyterlab_cli_extension.session_state import SessionState

logger = logging.getLogger(__name__)


class JupyterLabCliExtensionApp(ExtensionApp):
    """Registers /jupyterlab-cli/* HTTP routes and WebSocket bridge."""

    name = "jupyterlab_cli_extension"
    load_other_extensions = True

    def initialize_settings(self) -> None:
        self.settings.update(
            {
                "jupyterlab_cli_state": SessionState(),
                "jupyterlab_cli_bridge": FrontendBridge(),
            }
        )
        logger.info("jupyterlab-cli extension settings initialized")

    def initialize_handlers(self) -> None:
        self.handlers.extend(
            [
                ("jupyterlab-cli/healthz", HealthHandler),
                ("jupyterlab-cli/sessions", SessionsHandler),
                (r"jupyterlab-cli/sessions/([^/]+)", SessionDeleteHandler),
                (r"jupyterlab-cli/sessions/([^/]+)/notebook", NotebookReadHandler),
                (r"jupyterlab-cli/sessions/([^/]+)/cells", CellsAddHandler),
                (r"jupyterlab-cli/sessions/([^/]+)/cells/([0-9]+)", CellItemHandler),
                (r"jupyterlab-cli/sessions/([^/]+)/execute-cell", ExecuteCellHandler),
                (r"jupyterlab-cli/sessions/([^/]+)/execute-code", ExecuteCodeHandler),
                (r"jupyterlab-cli/sessions/([^/]+)/restart", RestartKernelHandler),
                ("jupyterlab-cli/kernels", KernelsListHandler),
                ("jupyterlab-cli/files", FilesListHandler),
                ("jupyterlab-cli/clipboard/image", ClipboardImageHandler),
                ("jupyterlab-cli/ws", BridgeWebSocketHandler),
            ]
        )
        logger.info("jupyterlab-cli HTTP/WebSocket handlers registered")


def _jupyter_server_extension_points() -> list[dict[str, object]]:
    return [
        {
            "module": "jupyterlab_cli_extension.extension",
            "app": JupyterLabCliExtensionApp,
        }
    ]
