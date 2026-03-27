---
name: jupyter-cli
description: >-
  jupyter-cli is a stateless HTTP client to the Jupyter server extension: configure
  server URL/token, attach to a notebook with per-path locks (use-notebook /
  unuse-notebook), read and edit .ipynb cells (add/read/update/delete), execute
  cells or ad-hoc code (streaming), list notebooks/files/kernels, restart kernels,
  and check status—with optional --json for scripts. Use when automating JupyterLab
  from the terminal or agents, coordinating locks via JUPYTER_CLI_SESSION, or
  avoiding local notebook state (all state on the server).
---

# jupyter-cli (agent skill)

**This file vs `README.md`:** `SKILL.md` is a minimal install + CLI map for agents. **`README.md`** has architecture, full flags, API routes, examples, and packaging—read it when details matter.

## Install

```bash
pip install jupyter-cli
```

Run **JupyterLab** (or Jupyter Server) in an environment where `jupyter-cli` is installed so the **`jupyter_cli_extension`** is available. Then use the `jupyter-cli` binary to talk to that server over HTTP.

## CLI shape

```text
jupyter-cli [OPTIONS] COMMAND [ARGS]...
```

**Global options** (before `COMMAND`):

| Option | Role |
|--------|------|
| `--json` | Machine-readable JSON (place **before** the subcommand, e.g. `jupyter-cli --json status`) |
| `--server-url TEXT` | Jupyter server base URL (overrides config / env) |
| `--token TEXT` | Auth token |
| `--session TEXT` | Stable session id for multi-client locking (or `JUPYTER_CLI_SESSION`) |

**Commands** (interact with notebooks on the server):

| Area | Commands |
|------|----------|
| Setup / health | `configure`, `status` |
| Notebook focus | `use-notebook`, `unuse-notebook`, `list-notebooks`, `read-notebook` |
| Cells | `add-cell`, `read-cell`, `update-cell`, `delete-cell`, `execute-cell`, `execute-code` |
| Kernels / files | `list-kernels`, `restart-kernel`, `list-files` |

Subcommand-specific flags: **`jupyter-cli <command> --help`**. Deep reference: **`README.md`**.

## Typical agent flow

1. **`jupyter-cli configure`** (or env: server URL + token).
2. Optionally **`export JUPYTER_CLI_SESSION=...`** for a stable lock identity.
3. **`jupyter-cli use-notebook <path/to/notebook.ipynb>`** to attach and lock.
4. Mutate or run cells with the cell / execute commands above.
5. **`jupyter-cli unuse-notebook`** when finished.

Do not assume the server is running; start JupyterLab first if needed.

## Reference

- Full docs, routes, and examples: **`README.md`** in this repository.
- Repo: [github.com/wenmin-wu/jupyter-cli](https://github.com/wenmin-wu/jupyter-cli)
