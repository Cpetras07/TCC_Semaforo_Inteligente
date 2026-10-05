"""Histórico leve em SQLite para apoiar a demonstração e o TCC."""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class HistoryStore:
    def __init__(self, path: str = "data/semaforo.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS traffic_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at REAL NOT NULL,
                    light TEXT NOT NULL,
                    total_vehicles INTEGER NOT NULL,
                    stopped_vehicles INTEGER NOT NULL,
                    emergency_active INTEGER NOT NULL,
                    emergency_confidence REAL NOT NULL,
                    manual_mode INTEGER NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    def record(self, status: dict[str, Any]) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO traffic_events (
                    recorded_at, light, total_vehicles, stopped_vehicles,
                    emergency_active, emergency_confidence, manual_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    status.get("light", "RED"),
                    int(status.get("total_vehicles", 0)),
                    int(status.get("stopped_vehicles", 0)),
                    int(bool(status.get("emergency_active", False))),
                    float(status.get("emergency_confidence", 0.0)),
                    int(bool(status.get("manual_mode", False))),
                ),
            )

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, recorded_at, light, total_vehicles, stopped_vehicles,
                       emergency_active, emergency_confidence, manual_mode
                FROM traffic_events
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
