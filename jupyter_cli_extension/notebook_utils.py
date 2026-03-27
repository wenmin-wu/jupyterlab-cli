"""Load/save notebooks via Jupyter contents_manager (async)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import nbformat
from nbformat.notebooknode import NotebookNode


async def load_notebook_node(contents_manager: Any, path: str) -> NotebookNode:
    model = await contents_manager.get(path, type="notebook", content=True)
    return nbformat.from_dict(model["content"])


async def save_notebook_node(contents_manager: Any, path: str, nb: NotebookNode) -> None:
    model = await contents_manager.get(path, type="notebook", content=False)
    model["content"] = nbformat.to_dict(nb)
    model["type"] = "notebook"
    await contents_manager.save(model, path)


async def ensure_parent_dirs(contents_manager: Any, path: str) -> None:
    """Create parent directories for a notebook path if missing."""
    parent = str(Path(path).parent).replace("\\", "/")
    if not parent or parent == ".":
        return
    if await _exists(contents_manager, parent):
        return
    gp = str(Path(parent).parent).replace("\\", "/")
    if gp and gp != ".":
        await ensure_parent_dirs(contents_manager, parent)
    model = {"type": "directory", "path": parent}
    await contents_manager.save(model, parent)


async def _exists(contents_manager: Any, path: str) -> bool:
    if hasattr(contents_manager, "exists"):
        return await contents_manager.exists(path)
    try:
        await contents_manager.get(path, type="directory", content=False)
        return True
    except Exception:  # noqa: BLE001
        return False
