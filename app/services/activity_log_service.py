"""Activity logging service using JSONL files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from app.utils.paths import LOGS_DIR


@dataclass
class ActivityEvent:
    """Serializable event entry for activity logs."""

    timestamp: str
    event: str
    status: str
    message: str
    details: dict


class ActivityLogService:
    """Persists activity events as JSONL for each app session."""

    def __init__(self, logs_dir: Path | None = None) -> None:
        self.logs_dir = logs_dir or LOGS_DIR
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.session_log_path = self.logs_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    def log(self, event: str, status: str, message: str, details: dict | None = None) -> None:
        payload = ActivityEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event=event,
            status=status,
            message=message,
            details=details or {},
        )
        with self.session_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload.__dict__, ensure_ascii=False) + "\n")

    def export_log(self, destination_path: str) -> Path:
        """Export current session log to a user-chosen .jsonl destination."""
        destination = Path(destination_path)
        if destination.suffix.lower() != ".jsonl":
            destination = destination.with_suffix(".jsonl")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.session_log_path, destination)
        return destination
