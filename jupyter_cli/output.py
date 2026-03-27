"""Human (rich) vs JSON output."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

try:
    from rich.console import Console
    from rich.json import JSON as RichJSON

    _console = Console(stderr=True)
except ImportError:
    _console = None


def emit(data: Any, *, json_mode: bool, out: TextIO = sys.stdout) -> None:
    if json_mode:
        out.write(json.dumps(data, default=str, indent=2))
        out.write("\n")
        return
    if _console is not None:
        if isinstance(data, (dict, list)):
            _console.print(RichJSON.from_data(data))
        else:
            _console.print(str(data))
    else:
        print(json.dumps(data, default=str, indent=2), file=out)
