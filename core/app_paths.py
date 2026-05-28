from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", app_root()))
    return Path(__file__).resolve().parent.parent


def data_file(name: str) -> Path:
    root = app_root()
    root.mkdir(parents=True, exist_ok=True)
    return root / name


def resource_file(relative_path: str) -> Path:
    return resource_root() / relative_path
