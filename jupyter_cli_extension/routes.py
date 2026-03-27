"""Tornado handlers for /jupyter-cli/* REST API and WebSocket bridge."""

from __future__ import annotations

import asyncio
import base64
import fnmatch
import json
import logging
import uuid
from pathlib import Path
from typing import Any

import nbformat
from jupyter_server.base.handlers import APIHandler
from nbformat.v4 import new_code_cell, new_markdown_cell, new_raw_cell
from tornado.web import HTTPError, authenticated
from tornado.websocket import WebSocketHandler

from jupyter_cli_extension import kernel_ops
from jupyter_cli_extension.notebook_utils import ensure_parent_dirs, load_notebook_node, save_notebook_node
from jupyter_cli_extension.session_state import SessionInfo, get_bridge, get_state

logger = logging.getLogger(__name__)

SESSION_HEADER = "X-Jupyter-CLI-Session"


def _session_from_request(handler: APIHandler) -> str:
    return handler.request.headers.get(SESSION_HEADER, "").strip()


def _require_session(handler: APIHandler) -> str:
    sid = _session_from_request(handler)
    if not sid:
        raise HTTPError(400, "Missing X-Jupyter-CLI-Session header")
    return sid


def _json_body(handler: APIHandler) -> dict[str, Any]:
    if not handler.request.body:
        return {}
    try:
        return json.loads(handler.request.body.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPError(400, f"Invalid JSON: {e}") from e


class HealthHandler(APIHandler):
    @authenticated
    async def get(self) -> None:
        self.set_header("Content-Type", "application/json")
        self.finish(
            json.dumps(
                {
                    "status": "ok",
                    "extension": "jupyter_cli_extension",
                }
            )
        )


class SessionsHandler(APIHandler):
    """GET list sessions; POST use-notebook."""

    @authenticated
    async def get(self) -> None:
        state = get_state(self)
        self.set_header("Content-Type", "application/json")
        self.finish(json.dumps({"sessions": state.list_sessions()}))

    @authenticated
    async def post(self) -> None:
        session_id = _require_session(self)
        body = _json_body(self)
        notebook_path = body.get("notebook_path", "").strip()
        force = bool(body.get("force", False))
        parents = bool(body.get("parents", False))
        if not notebook_path:
            raise HTTPError(400, "notebook_path required")

        state = get_state(self)
        serverapp = self.settings["serverapp"]
        cm = serverapp.contents_manager
        km = serverapp.kernel_manager
        sm = serverapp.session_manager

        if not state.locks.acquire(notebook_path, session_id, force):
            raise HTTPError(409, "Notebook locked by another session")

        if parents:
            await ensure_parent_dirs(cm, notebook_path)

        try:
            await cm.get(notebook_path, type="notebook", content=False)
        except Exception:  # noqa: BLE001
            model = {
                "type": "notebook",
                "path": notebook_path,
                "content": nbformat.v4.new_notebook(),
            }
            await cm.save(model, notebook_path)

        kernel_id = await km.start_kernel()
        try:
            await sm.create_session(
                path=notebook_path,
                kernel_id=kernel_id,
                type="notebook",
                name=notebook_path,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("create_session: %s", e)

        state.set_session(session_id, SessionInfo(notebook_path=notebook_path, kernel_id=kernel_id))
        get_bridge(self).broadcast(
            {"type": "notebook_attached", "path": notebook_path, "session_id": session_id}
        )

        self.set_header("Content-Type", "application/json")
        self.finish(
            json.dumps(
                {
                    "session_id": session_id,
                    "notebook_path": notebook_path,
                    "kernel_id": kernel_id,
                }
            )
        )


class SessionDeleteHandler(APIHandler):
    """DELETE unuse-notebook."""

    @authenticated
    async def delete(self, session_id: str) -> None:
        state = get_state(self)
        info = state.remove(session_id)
        if info:
            state.locks.release_path(info.notebook_path, session_id)
        get_bridge(self).broadcast({"type": "session_closed", "session_id": session_id})
        self.set_status(204)
        self.finish()


class NotebookReadHandler(APIHandler):
    @authenticated
    async def get(self, session_id: str) -> None:
        state = get_state(self)
        info = state.get(session_id)
        if not info:
            raise HTTPError(404, "Unknown session")
        fmt = self.get_argument("format", "brief")
        nb = await load_notebook_node(self.settings["serverapp"].contents_manager, info.notebook_path)
        cells = []
        for i, cell in enumerate(nb.cells):
            entry: dict[str, Any] = {
                "index": i,
                "cell_type": cell.cell_type,
                "source": cell.source,
            }
            if fmt == "detailed" and cell.cell_type == "code":
                entry["outputs"] = [nbformat.output_to_dict(o) for o in cell.outputs]
            cells.append(entry)
        self.set_header("Content-Type", "application/json")
        self.finish(
            json.dumps(
                {
                    "path": info.notebook_path,
                    "nbformat": nb.nbformat,
                    "cells": cells,
                }
            )
        )


class CellsAddHandler(APIHandler):
    @authenticated
    async def post(self, session_id: str) -> None:
        _require_session(self)
        state = get_state(self)
        info = state.get(session_id)
        if not info:
            raise HTTPError(404, "Unknown session")
        body = _json_body(self)
        cell_type = body.get("cell_type", "code")
        content = body.get("content", "")
        index = body.get("index")
        cm = self.settings["serverapp"].contents_manager
        nb = await load_notebook_node(cm, info.notebook_path)
        if cell_type == "code":
            cell = new_code_cell(content)
        elif cell_type == "markdown":
            cell = new_markdown_cell(content)
        elif cell_type == "raw":
            cell = new_raw_cell(content)
        else:
            raise HTTPError(400, "cell_type must be code, markdown, or raw")
        if index is None:
            nb.cells.append(cell)
            idx = len(nb.cells) - 1
        else:
            idx = int(index)
            nb.cells.insert(idx, cell)
        await save_notebook_node(cm, info.notebook_path, nb)
        get_bridge(self).broadcast({"type": "notebook_updated", "path": info.notebook_path})
        self.set_header("Content-Type", "application/json")
        self.finish(json.dumps({"index": idx}))


class CellItemHandler(APIHandler):
    """GET/PUT/DELETE single cell."""

    @authenticated
    async def get(self, session_id: str, index: str) -> None:
        state = get_state(self)
        info = state.get(session_id)
        if not info:
            raise HTTPError(404, "Unknown session")
        i = int(index)
        no_outputs = self.get_argument("no_outputs", None) is not None
        nb = await load_notebook_node(self.settings["serverapp"].contents_manager, info.notebook_path)
        if i < 0 or i >= len(nb.cells):
            raise HTTPError(400, "Cell index out of range")
        cell = nb.cells[i]
        out: dict[str, Any] = {
            "index": i,
            "cell_type": cell.cell_type,
            "source": cell.source,
        }
        if not no_outputs and cell.cell_type == "code":
            out["outputs"] = [nbformat.output_to_dict(o) for o in cell.outputs]
        self.set_header("Content-Type", "application/json")
        self.finish(json.dumps(out))

    @authenticated
    async def put(self, session_id: str, index: str) -> None:
        _require_session(self)
        state = get_state(self)
        info = state.get(session_id)
        if not info:
            raise HTTPError(404, "Unknown session")
        i = int(index)
        body = _json_body(self)
        content = body.get("content", "")
        cm = self.settings["serverapp"].contents_manager
        nb = await load_notebook_node(cm, info.notebook_path)
        if i < 0 or i >= len(nb.cells):
            raise HTTPError(400, "Cell index out of range")
        nb.cells[i].source = content
        await save_notebook_node(cm, info.notebook_path, nb)
        get_bridge(self).broadcast({"type": "notebook_updated", "path": info.notebook_path})
        self.finish(json.dumps({"ok": True}))

    @authenticated
    async def delete(self, session_id: str, index: str) -> None:
        _require_session(self)
        state = get_state(self)
        info = state.get(session_id)
        if not info:
            raise HTTPError(404, "Unknown session")
        i = int(index)
        cm = self.settings["serverapp"].contents_manager
        nb = await load_notebook_node(cm, info.notebook_path)
        if i < 0 or i >= len(nb.cells):
            raise HTTPError(400, "Cell index out of range")
        del nb.cells[i]
        await save_notebook_node(cm, info.notebook_path, nb)
        get_bridge(self).broadcast({"type": "notebook_updated", "path": info.notebook_path})
        self.set_status(204)
        self.finish()


class ExecuteCellHandler(APIHandler):
    @authenticated
    async def post(self, session_id: str) -> None:
        state = get_state(self)
        info = state.get(session_id)
        if not info:
            raise HTTPError(404, "Unknown session")
        body = _json_body(self)
        index = int(body.get("index", 0))
        timeout = body.get("timeout")
        stream = bool(body.get("stream", True))
        to = float(timeout) if timeout is not None else None

        cm = self.settings["serverapp"].contents_manager
        km = self.settings["serverapp"].kernel_manager
        nb = await load_notebook_node(cm, info.notebook_path)
        if index < 0 or index >= len(nb.cells):
            raise HTTPError(400, "Cell index out of range")
        cell = nb.cells[index]
        if cell.cell_type != "code":
            raise HTTPError(400, "Not a code cell")
        code = cell.source

        if stream:
            self.set_header("Content-Type", "text/event-stream")
            self.set_header("Cache-Control", "no-cache")
            self.set_header("Connection", "keep-alive")

            def run_stream() -> list[str]:
                return list(
                    kernel_ops.stream_kernel_execute(km, info.kernel_id, code, to)
                )

            chunks = await asyncio.to_thread(run_stream)
            for ch in chunks:
                self.write(f"data: {json.dumps({'text': ch})}\n\n")
                await self.flush()
            self.write(f"data: {json.dumps({'done': True})}\n\n")
            await self.flush()
            self.finish()
        else:
            lines, out_dir = await asyncio.to_thread(
                kernel_ops.collect_kernel_execute, km, info.kernel_id, code, to
            )
            self.set_header("Content-Type", "application/json")
            self.finish(
                json.dumps(
                    {
                        "lines": lines,
                        "output_dir": out_dir,
                    }
                )
            )


class ExecuteCodeHandler(APIHandler):
    @authenticated
    async def post(self, session_id: str) -> None:
        state = get_state(self)
        info = state.get(session_id)
        if not info:
            raise HTTPError(404, "Unknown session")
        body = _json_body(self)
        code = body.get("code", "")
        timeout = body.get("timeout")
        stream = bool(body.get("stream", True))
        to = float(timeout) if timeout is not None else None
        km = self.settings["serverapp"].kernel_manager

        if stream:
            self.set_header("Content-Type", "text/event-stream")
            self.set_header("Cache-Control", "no-cache")

            def run_stream() -> list[str]:
                return list(kernel_ops.stream_kernel_execute(km, info.kernel_id, code, to))

            chunks = await asyncio.to_thread(run_stream)
            for ch in chunks:
                self.write(f"data: {json.dumps({'text': ch})}\n\n")
                await self.flush()
            self.write(f"data: {json.dumps({'done': True})}\n\n")
            await self.flush()
            self.finish()
        else:
            lines, out_dir = await asyncio.to_thread(
                kernel_ops.collect_kernel_execute, km, info.kernel_id, code, to
            )
            self.set_header("Content-Type", "application/json")
            self.finish(json.dumps({"lines": lines, "output_dir": out_dir}))


class RestartKernelHandler(APIHandler):
    @authenticated
    async def post(self, session_id: str) -> None:
        state = get_state(self)
        info = state.get(session_id)
        if not info:
            raise HTTPError(404, "Unknown session")
        km = self.settings["serverapp"].kernel_manager
        await asyncio.to_thread(kernel_ops.restart_kernel, km, info.kernel_id)
        self.finish(json.dumps({"ok": True}))


class KernelsListHandler(APIHandler):
    @authenticated
    async def get(self) -> None:
        km = self.settings["serverapp"].kernel_manager
        kernels = km.list_kernels()
        self.finish(json.dumps({"kernels": kernels}))


class FilesListHandler(APIHandler):
    @authenticated
    async def get(self) -> None:
        path = self.get_argument("path", "") or ""
        pattern = self.get_argument("pattern", "*")
        cm = self.settings["serverapp"].contents_manager
        try:
            model = await cm.get(path, type="directory", content=True)
        except Exception as e:  # noqa: BLE001
            raise HTTPError(404, str(e)) from e
        items = []
        for ent in model.get("content", []):
            name = ent.get("name", "")
            if fnmatch.fnmatch(name, pattern):
                items.append(ent)
        self.finish(json.dumps({"path": path, "content": items}))


class ClipboardImageHandler(APIHandler):
    @authenticated
    async def post(self) -> None:
        body = self.request.body
        if not body:
            raise HTTPError(400, "empty body")
        name = f"/tmp/clipboard_{uuid.uuid4().hex}.png"
        p = Path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        if body[:8] == b"\x89PNG\r\n\x1a\n":
            p.write_bytes(body)
        else:
            try:
                raw = base64.b64decode(body)
                p.write_bytes(raw)
            except Exception:  # noqa: BLE001
                p.write_bytes(body)
        self.finish(json.dumps({"path": str(p)}))


class BridgeWebSocketHandler(WebSocketHandler):
    def check_origin(self, origin: str) -> bool:
        return True

    def open(self, *args: Any, **kwargs: Any) -> None:
        token = self.get_argument("token", default=None)
        app = self.settings.get("serverapp")
        if app and app.token and token != app.token:
            self.close(1008, "invalid token")
            return
        bridge = self.settings["jupyter_cli_bridge"]
        bridge.register(self)

    def on_close(self) -> None:
        bridge = self.settings.get("jupyter_cli_bridge")
        if bridge:
            bridge.unregister(self)

    def on_message(self, message: str | bytes) -> None:
        pass
