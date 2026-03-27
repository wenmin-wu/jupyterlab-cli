"""Jupyter Server ExtensionApp: REST API + WebSocket bridge for jupyter-cli."""

from __future__ import annotations

import logging

from jupyter_server.extension.application import ExtensionApp

from jupyter_cli_extension.frontend_bridge import FrontendBridge
from jupyter_cli_extension.routes import (
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
from jupyter_cli_extension.session_state import SessionState

logger = logging.getLogger(__name__)


class JupyterCliExtensionApp(ExtensionApp):
    """Registers /jupyter-cli/* HTTP routes and WebSocket bridge."""

    name = "jupyter_cli_extension"
    load_other_extensions = True

    def initialize_settings(self) -> None:
        self.settings.update(
            {
                "jupyter_cli_state": SessionState(),
                "jupyter_cli_bridge": FrontendBridge(),
            }
        )
        logger.info("jupyter-cli extension settings initialized")

    def initialize_handlers(self) -> None:
        self.handlers.extend(
            [
                ("jupyter-cli/healthz", HealthHandler),
                ("jupyter-cli/sessions", SessionsHandler),
                (r"jupyter-cli/sessions/([^/]+)", SessionDeleteHandler),
                (r"jupyter-cli/sessions/([^/]+)/notebook", NotebookReadHandler),
                (r"jupyter-cli/sessions/([^/]+)/cells", CellsAddHandler),
                (r"jupyter-cli/sessions/([^/]+)/cells/([0-9]+)", CellItemHandler),
                (r"jupyter-cli/sessions/([^/]+)/execute-cell", ExecuteCellHandler),
                (r"jupyter-cli/sessions/([^/]+)/execute-code", ExecuteCodeHandler),
                (r"jupyter-cli/sessions/([^/]+)/restart", RestartKernelHandler),
                ("jupyter-cli/kernels", KernelsListHandler),
                ("jupyter-cli/files", FilesListHandler),
                ("jupyter-cli/clipboard/image", ClipboardImageHandler),
                ("jupyter-cli/ws", BridgeWebSocketHandler),
            ]
        )
        logger.info("jupyter-cli HTTP/WebSocket handlers registered")


def _jupyter_server_extension_points() -> list[dict[str, object]]:
    return [
        {
            "module": "jupyter_cli_extension.extension",
            "app": JupyterCliExtensionApp,
        }
    ]
