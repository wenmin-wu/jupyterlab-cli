"""XDG config file + environment variable resolution."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

ENV_SERVER_URL = "JUPYTER_CLI_SERVER_URL"
ENV_TOKEN = "JUPYTER_CLI_TOKEN"
ENV_SESSION = "JUPYTER_CLI_SESSION"


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(base) / "jupyter-cli"


def config_path() -> Path:
    return config_dir() / "config.json"


def default_session_id() -> str:
    return str(os.getpid())


def load_config_file() -> dict[str, Any]:
    p = config_path()
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_config_file(data: dict[str, Any]) -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    config_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def resolve_config(
    cli_server_url: Optional[str] = None,
    cli_token: Optional[str] = None,
    cli_session: Optional[str] = None,
) -> dict[str, str]:
    """CLI flags > env > file."""
    file_data = load_config_file()
    server_url = (
        cli_server_url
        or os.environ.get(ENV_SERVER_URL)
        or file_data.get("server_url")
        or "http://localhost:8888"
    )
    token = cli_token or os.environ.get(ENV_TOKEN) or file_data.get("token") or ""
    session = cli_session or os.environ.get(ENV_SESSION) or file_data.get("session_id") or default_session_id()
    return {
        "server_url": server_url.rstrip("/"),
        "token": token,
        "session_id": session,
    }
