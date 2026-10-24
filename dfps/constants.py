"""Read-only access to the paper's stated constants (config/paper_constants.yaml)."""
from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import yaml

_PATH = Path(__file__).resolve().parent.parent / "config" / "paper_constants.yaml"


def _freeze(x):
    if isinstance(x, dict):
        return MappingProxyType({k: _freeze(v) for k, v in x.items()})
    if isinstance(x, list):
        return tuple(_freeze(v) for v in x)
    return x


PAPER = _freeze(yaml.safe_load(_PATH.read_text(encoding="utf-8")))
