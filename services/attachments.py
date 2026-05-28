from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def attachment_path(value: str | None) -> Path | None:
    raw = (value or "").strip()
    if not raw:
        return None
    return Path(raw)


def attachment_name(value: str | None) -> str:
    path = attachment_path(value)
    if path is None:
        return "Sem anexo"
    return path.name


def open_attachment(value: str | None) -> Path:
    path = attachment_path(value)
    if path is None:
        raise ValueError("Nenhum anexo disponível para esta movimentação.")
    if not path.exists():
        raise FileNotFoundError(f"Anexo não encontrado: {path}")

    if hasattr(os, "startfile"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
    return path
