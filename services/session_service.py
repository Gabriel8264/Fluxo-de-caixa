from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from core.app_paths import data_file

STATE_FILE = data_file("session_state.json")


class SessionService:
    def __init__(self, state_file: Path | None = None) -> None:
        self.state_file = state_file or STATE_FILE

    def get_active_day(self) -> str:
        if not self.state_file.exists():
            return date.today().isoformat()
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return date.today().isoformat()
        return data.get("active_day") or date.today().isoformat()

    def start_day(self, target_day: str | None = None) -> str:
        active_day = target_day or date.today().isoformat()
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps({"active_day": active_day}, indent=2), encoding="utf-8")
        return active_day
