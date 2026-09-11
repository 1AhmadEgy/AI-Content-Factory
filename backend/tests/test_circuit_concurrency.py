from __future__ import annotations

import multiprocessing as mp
import time
from pathlib import Path

from backend.app.infrastructure.resilience import SQLiteCircuitBreaker
from backend.app.infrastructure.sqlite import SQLiteStore


def _attempt(db_path: str, name: str, result_queue) -> None:
    store = SQLiteStore(db_path)
    breaker = SQLiteCircuitBreaker(store, name, fail_threshold=1, open_duration=0.15, half_open_max_calls=2, success_threshold=2)
    result_queue.put(breaker.acquire())


def test_half_open_limit_across_processes(tmp_path: Path) -> None:
    db_path = str(tmp_path / "circuit.db")
    store = SQLiteStore(db_path)
    breaker = SQLiteCircuitBreaker(store, "process-cb", fail_threshold=1, open_duration=0.15, half_open_max_calls=2, success_threshold=2)
    assert breaker.acquire()
    breaker.record_failure()
    assert not breaker.acquire()
    time.sleep(0.2)

    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    processes = [ctx.Process(target=_attempt, args=(db_path, "process-cb", queue)) for _ in range(10)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=10)
    for process in processes:
        assert process.exitcode == 0

    results = [queue.get(timeout=2) for _ in processes]
    assert sum(results) == 2
