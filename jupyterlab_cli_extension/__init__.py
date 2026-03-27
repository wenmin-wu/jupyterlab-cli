"""Jupyter Server extension for jupyterlab-cli REST API and WebSocket bridge."""

from jupyterlab_cli_extension.extension import JupyterLabCliExtensionApp, _jupyter_server_extension_points

__version__ = "0.1.0"
__author__ = "Wenmin Wu"
__author_email__ = "wuwenmin1991@gmail.com"
__url__ = "https://github.com/wenmin-wu/jupyterlab-cli"

__all__ = ["__version__", "JupyterLabCliExtensionApp", "_jupyter_server_extension_points"]
