"""HTTP client for jupyterlab-cli server extension."""

from __future__ import annotations

import json
from typing import Any, Iterator, Optional

import requests

SESSION_HEADER = "X-JupyterLab-CLI-Session"


class JupyterLabCliClient:
    def __init__(self, server_url: str, token: str, session_id: str) -> None:
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.session_id = session_id
        self._s = requests.Session()

    def _params(self) -> dict[str, str]:
        return {"token": self.token} if self.token else {}

    def _headers(self) -> dict[str, str]:
        return {SESSION_HEADER: self.session_id}

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return self.server_url + path

    def health(self) -> dict[str, Any]:
        r = self._s.get(self._url("/jupyterlab-cli/healthz"), params=self._params(), headers=self._headers(), timeout=30)
        r.raise_for_status()
        return r.json()

    def list_sessions(self) -> dict[str, Any]:
        r = self._s.get(self._url("/jupyterlab-cli/sessions"), params=self._params(), headers=self._headers(), timeout=60)
        r.raise_for_status()
        return r.json()

    def use_notebook(self, notebook_path: str, *, force: bool = False, parents: bool = False) -> dict[str, Any]:
        r = self._s.post(
            self._url("/jupyterlab-cli/sessions"),
            params=self._params(),
            headers=self._headers(),
            json={"notebook_path": notebook_path, "force": force, "parents": parents},
            timeout=120,
        )
        if r.status_code == 409:
            raise requests.HTTPError("409 Conflict: notebook locked", response=r)
        r.raise_for_status()
        return r.json()

    def unuse_notebook(self) -> None:
        r = self._s.delete(
            self._url(f"/jupyterlab-cli/sessions/{self.session_id}"),
            params=self._params(),
            headers=self._headers(),
            timeout=60,
        )
        if r.status_code not in (200, 204):
            r.raise_for_status()

    def read_notebook(self, fmt: str = "brief") -> dict[str, Any]:
        r = self._s.get(
            self._url(f"/jupyterlab-cli/sessions/{self.session_id}/notebook"),
            params={**self._params(), "format": fmt},
            headers=self._headers(),
            timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def add_cell(self, cell_type: str, content: str, index: Optional[int] = None) -> dict[str, Any]:
        body: dict[str, Any] = {"cell_type": cell_type, "content": content}
        if index is not None:
            body["index"] = index
        r = self._s.post(
            self._url(f"/jupyterlab-cli/sessions/{self.session_id}/cells"),
            params=self._params(),
            headers=self._headers(),
            json=body,
            timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def read_cell(self, index: int, *, no_outputs: bool = False) -> dict[str, Any]:
        params = {**self._params()}
        if no_outputs:
            params["no_outputs"] = "1"
        r = self._s.get(
            self._url(f"/jupyterlab-cli/sessions/{self.session_id}/cells/{index}"),
            params=params,
            headers=self._headers(),
            timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def update_cell(self, index: int, content: str) -> dict[str, Any]:
        r = self._s.put(
            self._url(f"/jupyterlab-cli/sessions/{self.session_id}/cells/{index}"),
            params=self._params(),
            headers=self._headers(),
            json={"content": content},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def delete_cell(self, index: int) -> None:
        r = self._s.delete(
            self._url(f"/jupyterlab-cli/sessions/{self.session_id}/cells/{index}"),
            params=self._params(),
            headers=self._headers(),
            timeout=60,
        )
        r.raise_for_status()

    def execute_cell(
        self,
        index: int,
        *,
        timeout: Optional[float] = None,
        stream: bool = True,
    ) -> Any:
        body: dict[str, Any] = {"index": index, "stream": stream}
        if timeout is not None:
            body["timeout"] = timeout
        r = self._s.post(
            self._url(f"/jupyterlab-cli/sessions/{self.session_id}/execute-cell"),
            params=self._params(),
            headers=self._headers(),
            json=body,
            stream=stream,
            timeout=timeout or 600,
        )
        r.raise_for_status()
        if stream:
            return r.iter_lines(decode_unicode=True)
        return r.json()

    def execute_code(
        self,
        code: str,
        *,
        timeout: Optional[float] = None,
        stream: bool = True,
    ) -> Any:
        body: dict[str, Any] = {"code": code, "stream": stream}
        if timeout is not None:
            body["timeout"] = timeout
        r = self._s.post(
            self._url(f"/jupyterlab-cli/sessions/{self.session_id}/execute-code"),
            params=self._params(),
            headers=self._headers(),
            json=body,
            stream=stream,
            timeout=timeout or 600,
        )
        r.raise_for_status()
        if stream:
            return r.iter_lines(decode_unicode=True)
        return r.json()

    def list_kernels(self) -> dict[str, Any]:
        r = self._s.get(self._url("/jupyterlab-cli/kernels"), params=self._params(), headers=self._headers(), timeout=60)
        r.raise_for_status()
        return r.json()

    def restart_kernel(self) -> dict[str, Any]:
        r = self._s.post(
            self._url(f"/jupyterlab-cli/sessions/{self.session_id}/restart"),
            params=self._params(),
            headers=self._headers(),
            timeout=120,
        )
        r.raise_for_status()
        return r.json()

    def list_files(self, path: str = "", pattern: str = "*") -> dict[str, Any]:
        r = self._s.get(
            self._url("/jupyterlab-cli/files"),
            params={**self._params(), "path": path, "pattern": pattern},
            headers=self._headers(),
            timeout=60,
        )
        r.raise_for_status()
        return r.json()


def parse_sse_lines(lines: Iterator[str]) -> Iterator[dict[str, Any]]:
    """Parse text/event-stream lines into JSON payloads."""
    for line in lines:
        if not line or not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload:
            continue
        try:
            yield json.loads(payload)
        except json.JSONDecodeError:
            yield {"raw": payload}
