from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from .sqlite import SQLiteStore


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True, slots=True)
class CircuitSnapshot:
    name: str
    state: CircuitState
    failures: int
    successes: int
    half_open_calls: int
    opened_at: float | None


class SQLiteCircuitBreaker:
    """Worker-shared circuit breaker using the project's existing SQLite source of truth."""

    def __init__(self, store: SQLiteStore, name: str, *, fail_threshold: int = 5,
                 open_duration: float = 60.0, half_open_max_calls: int = 2,
                 success_threshold: int = 2) -> None:
        if fail_threshold <= 0 or open_duration <= 0 or half_open_max_calls <= 0 or success_threshold <= 0:
            raise ValueError("circuit breaker thresholds must be positive")
        self.store = store
        self.name = name
        self.fail_threshold = fail_threshold
        self.open_duration = open_duration
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.store._lock, self.store.connection:
            self.store.connection.execute("""CREATE TABLE IF NOT EXISTS provider_circuit_breakers (
                name TEXT PRIMARY KEY, state TEXT NOT NULL,
                failures INTEGER NOT NULL DEFAULT 0, successes INTEGER NOT NULL DEFAULT 0,
                half_open_calls INTEGER NOT NULL DEFAULT 0, opened_at REAL
            )""")

    def acquire(self) -> bool:
        now = time.time()
        with self.store._lock:
            conn = self.store.connection
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("SELECT * FROM provider_circuit_breakers WHERE name=?", (self.name,)).fetchone()
                if row is None:
                    conn.execute("INSERT INTO provider_circuit_breakers(name,state) VALUES(?,?)", (self.name, CircuitState.CLOSED.value))
                    conn.commit()
                    return True
                state = CircuitState(row["state"])
                if state is CircuitState.CLOSED:
                    conn.commit()
                    return True
                if state is CircuitState.OPEN:
                    opened_at = row["opened_at"]
                    if opened_at is None or now - float(opened_at) < self.open_duration:
                        conn.commit()
                        return False
                    conn.execute("UPDATE provider_circuit_breakers SET state=?, successes=0, half_open_calls=1 WHERE name=?", (CircuitState.HALF_OPEN.value, self.name))
                    conn.commit()
                    return True
                if int(row["half_open_calls"]) >= self.half_open_max_calls:
                    conn.commit()
                    return False
                conn.execute("UPDATE provider_circuit_breakers SET half_open_calls=half_open_calls+1 WHERE name=?", (self.name,))
                conn.commit()
                return True
            except Exception:
                conn.rollback()
                raise

    def record_success(self) -> None:
        with self.store._lock:
            conn = self.store.connection
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("SELECT * FROM provider_circuit_breakers WHERE name=?", (self.name,)).fetchone()
                if row is None:
                    conn.execute("INSERT INTO provider_circuit_breakers(name,state) VALUES(?,?)", (self.name, CircuitState.CLOSED.value))
                elif row["state"] == CircuitState.HALF_OPEN.value:
                    successes = int(row["successes"]) + 1
                    if successes >= self.success_threshold:
                        conn.execute("UPDATE provider_circuit_breakers SET state=?, failures=0, successes=0, half_open_calls=0, opened_at=NULL WHERE name=?", (CircuitState.CLOSED.value, self.name))
                    else:
                        conn.execute("UPDATE provider_circuit_breakers SET successes=? WHERE name=?", (successes, self.name))
                else:
                    conn.execute("UPDATE provider_circuit_breakers SET failures=0 WHERE name=?", (self.name,))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def record_failure(self) -> None:
        now = time.time()
        with self.store._lock:
            conn = self.store.connection
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("SELECT * FROM provider_circuit_breakers WHERE name=?", (self.name,)).fetchone()
                if row is None:
                    failures = 1
                    state = CircuitState.OPEN.value if failures >= self.fail_threshold else CircuitState.CLOSED.value
                    conn.execute("INSERT INTO provider_circuit_breakers(name,state,failures,opened_at) VALUES(?,?,?,?)", (self.name, state, failures, now if state == CircuitState.OPEN.value else None))
                elif row["state"] == CircuitState.HALF_OPEN.value:
                    conn.execute("UPDATE provider_circuit_breakers SET state=?, opened_at=?, successes=0, half_open_calls=0 WHERE name=?", (CircuitState.OPEN.value, now, self.name))
                else:
                    failures = int(row["failures"]) + 1
                    if failures >= self.fail_threshold:
                        conn.execute("UPDATE provider_circuit_breakers SET state=?, failures=?, opened_at=? WHERE name=?", (CircuitState.OPEN.value, failures, now, self.name))
                    else:
                        conn.execute("UPDATE provider_circuit_breakers SET failures=? WHERE name=?", (failures, self.name))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def snapshot(self) -> CircuitSnapshot:
        with self.store._lock:
            row = self.store.connection.execute("SELECT * FROM provider_circuit_breakers WHERE name=?", (self.name,)).fetchone()
            if row is None:
                return CircuitSnapshot(self.name, CircuitState.CLOSED, 0, 0, 0, None)
            return CircuitSnapshot(self.name, CircuitState(row["state"]), int(row["failures"]), int(row["successes"]), int(row["half_open_calls"]), row["opened_at"])
