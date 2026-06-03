from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from core.app_paths import data_file

STATE_FILE = data_file("session_state.json")


class SessionService:
    def __init__(self, state_file: Path | None = None) -> None:
        self.state_file = state_file or STATE_FILE

    def get_active_day(self) -> str:
        state, needs_write = self._load_state()
        if needs_write:
            self._write_state(state)
        return str(state["active_day"])

    def start_day(self, target_day: str | None = None) -> str:
        state, _ = self._load_state()
        active_day = self._normalize_active_day(target_day) if target_day else date.today().isoformat()
        state["active_day"] = active_day
        self._write_state(state)
        return active_day

    def _load_state(self) -> tuple[dict[str, object], bool]:
        default_state = {"active_day": date.today().isoformat()}
        if not self.state_file.exists():
            return default_state, True

        try:
            raw_content = self.state_file.read_text(encoding="utf-8")
            data = json.loads(raw_content)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return default_state, True

        if not isinstance(data, dict):
            return default_state, True

        state = dict(data)
        normalized_day = self._normalize_active_day(state.get("active_day"))
        needs_write = normalized_day != state.get("active_day")
        state["active_day"] = normalized_day
        return state, needs_write

    def _write_state(self, state: dict[str, object]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _normalize_active_day(value: object) -> str:
        if isinstance(value, str):
            raw = value.strip()
            for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(raw, pattern).date().isoformat()
                except ValueError:
                    continue
        return date.today().isoformat()
