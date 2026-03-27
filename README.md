# jupyterlab-cli

A CLI tool and JupyterLab extension for AI agents to manage Jupyter notebooks. Every CLI command is a single HTTP call — no local state. The package also ships frontend plugins for terminal copy-on-select, browser-to-server clipboard image sync, and a “Copy Context” button for notebook cells.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ JupyterLab Server Process                                   │
│                                                             │
│  jupyterlab_cli_extension (server extension)                 │
│    REST handlers: /jupyterlab-cli/* (Tornado)                  │
│    Lock registry: in-memory, one lock per notebook          │
│    contents_manager: notebook read/write                    │
│    kernel_manager: kernel start/execute/restart           │
│    Frontend bridge: WebSocket relay to browser             │
│    Clipboard handler: POST /jupyterlab-cli/clipboard/image    │
│                                                             │
│  jupyterlab-cli-frontend (labextension)                       │
│    Frontend bridge plugin: routes cell ops via browser      │
│    Copy-on-select plugin: terminal text → clipboard         │
│    Clipboard image plugin: browser image → server file      │
│    Copy Context plugin: selection → JSON clipboard          │
│                                                             │
│  Streaming SSE: execute-cell / execute-code                 │
└─────────────────────────────────────────────────────────────┘

jupyterlab-cli (CLI) — pure HTTP client, stateless
```

## How it works

1. **Server extension (`jupyterlab_cli_extension/`)** — A Python package that registers Tornado HTTP handlers on the running Jupyter server. It manages sessions, notebook locks, cell CRUD, and kernel execution. It communicates with the browser via a WebSocket bridge so cell operations update the JupyterLab UI in real time.

2. **Frontend extension (`src/` → `jupyterlab_cli_extension/labextension/`)** — TypeScript plugins compiled into a JupyterLab labextension. It handles the browser-side WebSocket bridge, terminal enhancements (copy-on-select and clipboard image sync), and a “Copy Context” floating button.

3. **CLI (`jupyterlab_cli/`)** — A Click-based command-line tool that makes HTTP calls to the server extension. It is stateless; all state lives on the server. It supports human-readable (rich) and machine-readable (`--json`) output.

## Installation

### From PyPI (recommended)

Install the published package (CLI + server extension + bundled JupyterLab frontend). **You do not need Node.js** on the machine where you run `pip install`.

```bash
pip install jupyterlab-cli
```

Upgrade to the latest release:

```bash
pip install -U jupyterlab-cli
```

**Includes**

- Command-line tool: `jupyterlab-cli`
- Jupyter **server extension**: `jupyterlab_cli_extension` (REST + WebSocket under `/jupyterlab-cli/…`)
- **JupyterLab labextension** (`jupyterlab-cli-frontend`), shipped inside the wheel

**Requires:** Python 3.10+.

**PyPI:** [pypi.org/project/jupyterlab-cli](https://pypi.org/project/jupyterlab-cli)

Use a virtual environment or Conda env where you also install **JupyterLab** (or at least `jupyter-server`) on the host that runs the notebook server, then start JupyterLab as usual—the extension is registered with the server.

### Verify after install

```bash
jupyter server extension list | grep jupyterlab_cli
jupyter labextension list | grep jupyterlab-cli-frontend
```

If the server extension does not appear, ensure you are using the same Python environment where `jupyterlab-cli` is installed, or run `jupyter server extension enable jupyterlab_cli_extension` (usually not needed when installing from the wheel).

### Install from a local checkout (development)

Installing from the repository builds the frontend during packaging via [hatch-jupyter-builder](https://github.com/jupyterlab/hatch-jupyter-builder) (`jlpm build:prod`). **Build-time:** Node.js + `jlpm` must be available (see `pyproject.toml`).

```bash
git clone https://github.com/wenmin-wu/jupyterlab-cli.git
cd jupyterlab-cli
pip install -e .
```

To **skip** the labextension build (Python-only):

```bash
export SKIP_JUPYTER_BUILDER=1
pip install -e .
```

Link the labextension for live frontend development:

```bash
jupyter labextension develop . --overwrite
```

### Building wheels locally (maintainers / CI)

Release wheels on PyPI include the labextension; building from a clean tree needs Node. Example:

```bash
pip install build
python -m build --wheel
# or: pip wheel . -w dist/
```

Install the produced wheel:

```bash
pip install dist/jupyterlab_cli-*-py3-none-any.whl
```

## Quick start

1. **Start JupyterLab** (extension loads automatically)

   ```bash
   jupyter lab --IdentityProvider.token mytoken
   ```

2. **Configure the CLI** (one-time, interactive)

   ```bash
   jupyterlab-cli configure
   ```

3. **Verify connection**

   ```bash
   jupyterlab-cli status
   ```

4. **Set your agent’s session**

   ```bash
   export JUPYTERLAB_CLI_SESSION=my-task
   ```

5. **Attach to a notebook**

   ```bash
   jupyterlab-cli use-notebook notebooks/analysis.ipynb --parents
   ```

6. **Work with cells**

   ```bash
   jupyterlab-cli add-cell --type code --content 'import pandas as pd'
   jupyterlab-cli execute-cell --index 0
   ```

7. **Release the lock when done**

   ```bash
   jupyterlab-cli unuse-notebook
   ```

## Configuration

- Config is stored in `~/.config/jupyterlab-cli/config.json` (XDG-compliant).
- **Resolution order:** CLI flags → environment variables → config file.

**Interactive setup** (prompts with current values as defaults):

```bash
jupyterlab-cli configure
```

**Non-interactive setup:**

```bash
jupyterlab-cli configure --server-url http://localhost:8888 --token mytoken
```

**Show current config:**

```bash
jupyterlab-cli configure --show
```

### Environment variables

| Environment variable     | Purpose              | Default              |
| ------------------------ | -------------------- | -------------------- |
| `JUPYTERLAB_CLI_SERVER_URL` | JupyterLab server URL | `http://localhost:8888` |
| `JUPYTERLAB_CLI_TOKEN`      | Server auth token    | (empty)              |
| `JUPYTERLAB_CLI_SESSION`    | Session ID for agent | Current PID          |

## Commands

### Connection

| Command | Description |
| ------- | ----------- |
| `configure [--server-url] [--token] [--show]` | Configure or display connection settings |
| `status` | Show connection health and active session info |

### Notebook management

| Command | Description |
| ------- | ----------- |
| `use-notebook <path> [--force] [--parents]` | Attach to notebook, acquire lock |
| `unuse-notebook` | Detach, release lock |
| `list-notebooks` | All active sessions across agents |
| `read-notebook [--format FORMAT]` | Show notebook structure; `FORMAT` is `brief` or `detailed` |

### Cell operations

| Command | Description |
| ------- | ----------- |
| `add-cell --type TYPE --content <text> [--index N]` | Insert a cell (`TYPE`: code, markdown, or raw) |
| `read-cell --index N [--no-outputs]` | Read cell source and outputs |
| `update-cell --index N --content <text>` | Replace cell source |
| `delete-cell --index N` | Remove a cell |

### Execution

| Command | Description |
| ------- | ----------- |
| `execute-cell --index N [--timeout] [--no-stream]` | Execute a cell, stream outputs |
| `execute-code --content <code> [--timeout] [--no-stream]` | Run ad-hoc code on kernel |

### Kernel & filesystem

| Command | Description |
| ------- | ----------- |
| `list-kernels` | Show all running kernels |
| `restart-kernel` | Restart this session’s kernel |
| `list-files [<path>] [--pattern]` | Browse the Jupyter root directory |

### Agent output mode

Use `--json` **before** the subcommand for machine-readable output:

```bash
jupyterlab-cli --json status
jupyterlab-cli --json read-cell --index 0
```

## Session management

Multiple agents can work on **different** notebooks concurrently. A notebook can only be locked by one session at a time.

```bash
# Agent A locks notebook1
JUPYTERLAB_CLI_SESSION=agent-a jupyterlab-cli use-notebook notebook1.ipynb

# Agent B locks notebook2 — OK
JUPYTERLAB_CLI_SESSION=agent-b jupyterlab-cli use-notebook notebook2.ipynb

# Agent C tries notebook1 — blocked (409)
JUPYTERLAB_CLI_SESSION=agent-c jupyterlab-cli use-notebook notebook1.ipynb

# Override a stale lock
JUPYTERLAB_CLI_SESSION=agent-c jupyterlab-cli use-notebook notebook1.ipynb --force
```

## Frontend plugins

The labextension ships four plugins, all auto-enabled on install:

### Frontend bridge

Routes `jupyterlab-cli` cell operations through the browser via WebSocket so JupyterLab’s UI updates in real time when cells are added, modified, or executed.

### Terminal copy-on-select

Automatically copies selected text in JupyterLab terminals to the clipboard. Configurable via **Settings → Terminal Copy-on-Select**.

### Clipboard image sync

Bridges your local clipboard to the remote server when pasting images in a JupyterLab terminal:

1. **Cmd+V** (with image in clipboard) → image is uploaded to the server, saved as `/tmp/clipboard_xxx.png`
2. Browser clipboard is replaced with the file path
3. **Cmd+V** again → pastes the path as text into the terminal (e.g. for Claude Code to read)

Configurable via **Settings → Terminal Clipboard Image Sync**.

### Copy Context button

A floating “Copy Context” button appears when selecting text in notebook cells or file editors. Clicking it copies a JSON object to the clipboard, for example:

```json
{
  "type": "notebook_cell",
  "content": "selected code...",
  "filePath": "notebooks/analysis.ipynb",
  "language": "python",
  "cellIndex": 3,
  "startLine": 1,
  "endLine": 5
}
```

Paste this into a Claude Code terminal to provide structured context.

## Streaming execution

`execute-cell` and `execute-code` stream output via SSE (Server-Sent Events) as it arrives:

```bash
jupyterlab-cli execute-cell --index 2
#  0%|          | 0/100 [00:00<?, ?it/s]
# 10%|█         | 10/100 [00:01<00:09]
# [done] ok (10.23s)
```

Use `--no-stream` to buffer output and save images to files:

```bash
jupyterlab-cli execute-cell --index 2 --no-stream
# Output saved to /tmp/a1b2c3d4e5f6/
#  /tmp/a1b2c3d4e5f6/1.txt
#  /tmp/a1b2c3d4e5f6/2.png
```

## Extension REST API

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/jupyterlab-cli/healthz` | Health check |
| GET | `/jupyterlab-cli/sessions` | List sessions |
| POST | `/jupyterlab-cli/sessions` | use-notebook |
| DELETE | `/jupyterlab-cli/sessions/{id}` | unuse-notebook |
| GET | `/jupyterlab-cli/sessions/{id}/notebook` | Read notebook |
| POST | `/jupyterlab-cli/sessions/{id}/cells` | Add cell |
| GET | `/jupyterlab-cli/sessions/{id}/cells/{n}` | Read cell |
| PUT | `/jupyterlab-cli/sessions/{id}/cells/{n}` | Update cell |
| DELETE | `/jupyterlab-cli/sessions/{id}/cells/{n}` | Delete cell |
| POST | `/jupyterlab-cli/sessions/{id}/execute-cell` | Execute cell (SSE) |
| POST | `/jupyterlab-cli/sessions/{id}/execute-code` | Execute code (SSE) |
| POST | `/jupyterlab-cli/sessions/{id}/restart` | Restart kernel |
| GET | `/jupyterlab-cli/kernels` | List kernels |
| GET | `/jupyterlab-cli/files` | List files |
| POST | `/jupyterlab-cli/clipboard/image` | Upload clipboard image |
| WS | `/jupyterlab-cli/ws` | Frontend bridge WebSocket |

## Project structure

Python HTTP/WebSocket handlers are implemented in `jupyterlab_cli_extension/routes.py` (the tree below matches the original modular layout; split into separate files if you prefer).

```
jupyterlab-cli/
├── jupyterlab_cli/                 # CLI (client-side)
│   ├── cli.py                   # Click entry point, configure, status
│   ├── client.py                # HTTP client (requests)
│   ├── config.py                # Config file + env var resolution
│   ├── output.py                # Dual-mode output (human/JSON)
│   └── commands/                # Subcommands
│       ├── notebook.py
│       ├── cell.py
│       ├── execute.py
│       └── kernel.py
├── jupyterlab_cli_extension/       # Server extension
│   ├── extension.py             # ExtensionApp, handler registration
│   ├── lock.py                  # Session lock registry
│   ├── kernel_ops.py            # Kernel execution helpers
│   ├── frontend_bridge.py       # WebSocket bridge singleton
│   └── handlers/                # Tornado request handlers
│       ├── session.py
│       ├── cell.py
│       ├── execute.py
│       ├── kernel.py
│       ├── clipboard.py
│       ├── ws.py
│       └── health.py
├── src/                         # Frontend (TypeScript)
│   ├── index.ts                 # Plugin registration
│   ├── copy-on-select.ts        # Terminal copy-on-select
│   ├── clipboard-image.ts       # Clipboard image sync
│   └── copy-context.ts          # Copy Context button
├── schema/                      # JupyterLab settings schemas
│   ├── copy-on-select.json
│   └── clipboard-image.json
├── style/                       # Frontend CSS
│   ├── index.css
│   └── base.css
├── jupyter-config/              # Auto-enable server extension
├── pyproject.toml               # Python project (hatchling)
├── package.json
├── tsconfig.json
└── SKILL.md                     # Agent skill definitions
```
