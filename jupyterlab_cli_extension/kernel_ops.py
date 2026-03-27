"""Kernel execution helpers (sync kernel client, used from async handlers via thread pool)."""

from __future__ import annotations

import base64
import json
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from jupyter_server.services.kernels.kernelmanager import MappingKernelManager


def _format_msg(msg: dict[str, Any]) -> str:
    """Human-readable line for SSE from an iopub message."""
    msg_type = msg.get("header", {}).get("msg_type", "")
    content = msg.get("content", {})
    if msg_type == "stream":
        return content.get("text", "")
    if msg_type == "error":
        return "\n".join(content.get("traceback", []))
    if msg_type in ("execute_result", "display_data"):
        data = content.get("data", {})
        if "text/plain" in data:
            return str(data["text/plain"])
        return json.dumps(data, default=str)[:2000]
    if msg_type == "status":
        return ""
    return ""


def stream_kernel_execute(
    kernel_manager: MappingKernelManager,
    kernel_id: str,
    code: str,
    timeout: Optional[float],
) -> Iterator[str]:
    """Yield text chunks from kernel execution (iopub), ending when idle."""
    try:
        km = kernel_manager.get_kernel(kernel_id)
    except KeyError as e:
        raise ValueError(f"Kernel {kernel_id!r} not found") from e
    if km is None:
        raise ValueError(f"Kernel {kernel_id!r} not found")
    client = km.client()
    client.wait_for_ready(timeout=timeout or 60)
    msg_id = client.execute(code)
    to = timeout or 60.0

    while True:
        try:
            msg = client.get_iopub_msg(timeout=to)
        except Exception:  # noqa: BLE001
            break
        if msg.get("parent_header", {}).get("msg_id") != msg_id:
            continue
        msg_type = msg.get("header", {}).get("msg_type", "")
        content = msg.get("content", {})
        if msg_type == "status" and content.get("execution_state") == "idle":
            break
        chunk = _format_msg(msg)
        if chunk:
            yield chunk


def collect_kernel_execute(
    kernel_manager: MappingKernelManager,
    kernel_id: str,
    code: str,
    timeout: Optional[float],
) -> tuple[List[str], Optional[str]]:
    """Collect text outputs; save binary image/png to temp files. Returns (text_lines, output_dir or None)."""
    try:
        km = kernel_manager.get_kernel(kernel_id)
    except KeyError as e:
        raise ValueError(f"Kernel {kernel_id!r} not found") from e
    if km is None:
        raise ValueError(f"Kernel {kernel_id!r} not found")
    client = km.client()
    client.wait_for_ready(timeout=timeout or 60)
    msg_id = client.execute(code)
    lines: List[str] = []
    images: List[Path] = []
    out_dir: Optional[Path] = None

    while True:
        msg = client.get_iopub_msg(timeout=timeout or 60)
        if msg.get("parent_header", {}).get("msg_id") != msg_id:
            continue
        msg_type = msg.get("header", {}).get("msg_type", "")
        content = msg.get("content", {})
        if msg_type == "stream":
            lines.append(content.get("text", ""))
        elif msg_type == "error":
            lines.extend(content.get("traceback", []))
        elif msg_type in ("execute_result", "display_data"):
            data = content.get("data", {})
            if "text/plain" in data:
                lines.append(str(data["text/plain"]))
            for mime in ("image/png", "image/jpeg"):
                if mime in data:
                    if out_dir is None:
                        out_dir = Path(tempfile.mkdtemp(prefix="jupyterlab_cli_"))
                    raw = data[mime]
                    if isinstance(raw, str):
                        blob = base64.b64decode(raw)
                    else:
                        blob = raw
                    ext = ".png" if "png" in mime else ".jpg"
                    p = out_dir / f"{len(images) + 1}{ext}"
                    p.write_bytes(blob)
                    images.append(p)
                    lines.append(str(p))
        if msg_type == "status" and content.get("execution_state") == "idle":
            break

    out_dir_str = str(out_dir) if out_dir else None
    return lines, out_dir_str


def interrupt_kernel(kernel_manager: MappingKernelManager, kernel_id: str) -> None:
    kernel_manager.interrupt_kernel(kernel_id)


def restart_kernel(kernel_manager: MappingKernelManager, kernel_id: str) -> None:
    kernel_manager.restart_kernel(kernel_id)


def new_id() -> str:
    return str(uuid.uuid4())
