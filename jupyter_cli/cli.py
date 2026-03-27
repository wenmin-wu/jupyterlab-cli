"""Click entry point for jupyter-cli."""

from __future__ import annotations

import sys
from typing import Any, Dict, Optional

import click
import requests

from jupyter_cli.client import JupyterCliClient, parse_sse_lines
from jupyter_cli import config as cfg
from jupyter_cli.output import emit


def _root_obj(ctx: click.Context) -> Dict[str, Any]:
    """Options live on the parent `main` group context."""
    return ctx.parent.obj if ctx.parent is not None else ctx.obj


def _client(ctx: click.Context) -> JupyterCliClient:
    o = _root_obj(ctx)
    c = cfg.resolve_config(
        cli_server_url=o.get("server_url"),
        cli_token=o.get("token"),
        cli_session=o.get("session"),
    )
    return JupyterCliClient(c["server_url"], c["token"], c["session_id"])


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--json", "json_mode", is_flag=True, help="Machine-readable JSON output")
@click.option("--server-url", default=None, envvar=cfg.ENV_SERVER_URL)
@click.option("--token", default=None, envvar=cfg.ENV_TOKEN)
@click.option("--session", "session_override", default=None, envvar=cfg.ENV_SESSION)
@click.pass_context
def main(
    ctx: click.Context,
    json_mode: bool,
    server_url: Optional[str],
    token: Optional[str],
    session_override: Optional[str],
) -> None:
    """jupyter-cli — manage notebooks via the Jupyter Server extension."""
    ctx.ensure_object(dict)
    ctx.obj["json_mode"] = json_mode
    ctx.obj["server_url"] = server_url
    ctx.obj["token"] = token
    ctx.obj["session"] = session_override


@main.command("configure")
@click.option("--server-url", default=None)
@click.option("--token", default=None)
@click.option("--show", is_flag=True)
@click.pass_context
def configure_cmd(ctx: click.Context, server_url: Optional[str], token: Optional[str], show: bool) -> None:
    """Write or display ~/.config/jupyter-cli/config.json"""
    ro = _root_obj(ctx)
    if show:
        data = cfg.load_config_file()
        merged = {**data, **cfg.resolve_config()}
        emit(merged, json_mode=ro["json_mode"])
        return
    current = cfg.load_config_file()
    if server_url is None and not ro["json_mode"]:
        server_url = click.prompt("Server URL", default=current.get("server_url", "http://localhost:8888"))
    if token is None and not ro["json_mode"]:
        token = click.prompt("Token", default=current.get("token", ""), show_default=False, hide_input=False)
    out = {
        "server_url": server_url or current.get("server_url", "http://localhost:8888"),
        "token": token if token is not None else current.get("token", ""),
        "session_id": current.get("session_id") or cfg.default_session_id(),
    }
    cfg.save_config_file(out)
    emit({"saved": cfg.config_path(), "config": out}, json_mode=ro["json_mode"])


@main.command("status")
@click.pass_context
def status_cmd(ctx: click.Context) -> None:
    """Check server health and session."""
    ro = _root_obj(ctx)
    cli = _client(ctx)
    try:
        h = cli.health()
        s = cli.list_sessions()
    except requests.RequestException as e:
        emit({"error": str(e)}, json_mode=ro["json_mode"])
        sys.exit(1)
    emit({"health": h, "sessions": s}, json_mode=ro["json_mode"])


@main.command("use-notebook")
@click.argument("path")
@click.option("--force", is_flag=True)
@click.option("--parents", is_flag=True)
@click.pass_context
def use_notebook_cmd(ctx: click.Context, path: str, force: bool, parents: bool) -> None:
    ro = _root_obj(ctx)
    cli = _client(ctx)
    try:
        r = cli.use_notebook(path, force=force, parents=parents)
    except requests.HTTPError as e:
        emit({"error": str(e), "status": getattr(e.response, "status_code", None)}, json_mode=ro["json_mode"])
        sys.exit(1)
    emit(r, json_mode=ro["json_mode"])


@main.command("unuse-notebook")
@click.pass_context
def unuse_notebook_cmd(ctx: click.Context) -> None:
    ro = _root_obj(ctx)
    cli = _client(ctx)
    try:
        cli.unuse_notebook()
    except requests.RequestException as e:
        emit({"error": str(e)}, json_mode=ro["json_mode"])
        sys.exit(1)
    emit({"ok": True}, json_mode=ro["json_mode"])


@main.command("list-notebooks")
@click.pass_context
def list_notebooks_cmd(ctx: click.Context) -> None:
    ro = _root_obj(ctx)
    cli = _client(ctx)
    emit(cli.list_sessions(), json_mode=ro["json_mode"])


@main.command("read-notebook")
@click.option("--format", "fmt", type=click.Choice(["brief", "detailed"]), default="brief")
@click.pass_context
def read_notebook_cmd(ctx: click.Context, fmt: str) -> None:
    ro = _root_obj(ctx)
    cli = _client(ctx)
    emit(cli.read_notebook(fmt), json_mode=ro["json_mode"])


@main.command("add-cell")
@click.option("--type", "cell_type", type=click.Choice(["code", "markdown", "raw"]), default="code")
@click.option("--content", required=True)
@click.option("--index", default=None, type=int)
@click.pass_context
def add_cell_cmd(ctx: click.Context, cell_type: str, content: str, index: Optional[int]) -> None:
    ro = _root_obj(ctx)
    cli = _client(ctx)
    emit(cli.add_cell(cell_type, content, index), json_mode=ro["json_mode"])


@main.command("read-cell")
@click.option("--index", required=True, type=int)
@click.option("--no-outputs", is_flag=True)
@click.pass_context
def read_cell_cmd(ctx: click.Context, index: int, no_outputs: bool) -> None:
    ro = _root_obj(ctx)
    cli = _client(ctx)
    emit(cli.read_cell(index, no_outputs=no_outputs), json_mode=ro["json_mode"])


@main.command("update-cell")
@click.option("--index", required=True, type=int)
@click.option("--content", required=True)
@click.pass_context
def update_cell_cmd(ctx: click.Context, index: int, content: str) -> None:
    ro = _root_obj(ctx)
    cli = _client(ctx)
    emit(cli.update_cell(index, content), json_mode=ro["json_mode"])


@main.command("delete-cell")
@click.option("--index", required=True, type=int)
@click.pass_context
def delete_cell_cmd(ctx: click.Context, index: int) -> None:
    ro = _root_obj(ctx)
    cli = _client(ctx)
    cli.delete_cell(index)
    emit({"ok": True}, json_mode=ro["json_mode"])


@main.command("execute-cell")
@click.option("--index", required=True, type=int)
@click.option("--timeout", default=None, type=float)
@click.option("--no-stream", "no_stream", is_flag=True)
@click.pass_context
def execute_cell_cmd(ctx: click.Context, index: int, timeout: Optional[float], no_stream: bool) -> None:
    ro = _root_obj(ctx)
    cli = _client(ctx)
    res = cli.execute_cell(index, timeout=timeout, stream=not no_stream)
    if no_stream:
        emit(res, json_mode=ro["json_mode"])
        return
    for chunk in parse_sse_lines(res):
        if ro["json_mode"]:
            emit(chunk, json_mode=True)
        else:
            t = chunk.get("text") or chunk.get("raw") or chunk
            if chunk.get("done"):
                continue
            sys.stdout.write(str(t))
            sys.stdout.flush()


@main.command("execute-code")
@click.option("--content", "code", required=True)
@click.option("--timeout", default=None, type=float)
@click.option("--no-stream", "no_stream", is_flag=True)
@click.pass_context
def execute_code_cmd(ctx: click.Context, code: str, timeout: Optional[float], no_stream: bool) -> None:
    ro = _root_obj(ctx)
    cli = _client(ctx)
    res = cli.execute_code(code, timeout=timeout, stream=not no_stream)
    if no_stream:
        emit(res, json_mode=ro["json_mode"])
        return
    for chunk in parse_sse_lines(res):
        if ro["json_mode"]:
            emit(chunk, json_mode=True)
        else:
            t = chunk.get("text") or chunk.get("raw") or chunk
            if chunk.get("done"):
                continue
            sys.stdout.write(str(t))
            sys.stdout.flush()


@main.command("list-kernels")
@click.pass_context
def list_kernels_cmd(ctx: click.Context) -> None:
    ro = _root_obj(ctx)
    cli = _client(ctx)
    emit(cli.list_kernels(), json_mode=ro["json_mode"])


@main.command("restart-kernel")
@click.pass_context
def restart_kernel_cmd(ctx: click.Context) -> None:
    ro = _root_obj(ctx)
    cli = _client(ctx)
    emit(cli.restart_kernel(), json_mode=ro["json_mode"])


@main.command("list-files")
@click.argument("path", required=False, default="")
@click.option("--pattern", default="*")
@click.pass_context
def list_files_cmd(ctx: click.Context, path: str, pattern: str) -> None:
    ro = _root_obj(ctx)
    cli = _client(ctx)
    emit(cli.list_files(path, pattern), json_mode=ro["json_mode"])


if __name__ == "__main__":
    main(obj={})
