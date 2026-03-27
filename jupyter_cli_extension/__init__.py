"""Jupyter Server extension for jupyter-cli REST API and WebSocket bridge."""

from jupyter_cli_extension.extension import JupyterCliExtensionApp, _jupyter_server_extension_points

__version__ = "0.1.0"
__author__ = "Wenmin Wu"
__author_email__ = "wuwenmin1991@gmail.com"
__url__ = "https://github.com/wenmin-wu/jupyter-cli"

__all__ = ["__version__", "JupyterCliExtensionApp", "_jupyter_server_extension_points"]
