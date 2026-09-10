from __future__ import annotations

import threading
import time

import pytest

from backend.app.orchestrator.worker_loop import WorkerLoop, WorkerLoopConfig


class FakeRuntime:
    def __init__(self, results: list[object | None], failures: int = 0) -> None:
        self.results = list(results)
        self.failures = failures
        self.recoveries = 0
        self.executions = 0
        self.started = threading.Event()

    def recover_expired(self) -> int:
        self.recoveries += 1
        return 0

    def execute_next(self, worker_id: str) -> object | None:
        self.executions += 1
        self.started.set()
        if self.failures:
            self.failures -= 1
            raise RuntimeError("temporary failure")
        return self.results.pop(0) if self.results else None


def test_run_once_executes_at_most_one_job() -> None:
    runtime = FakeRuntime([object()])
    loop = WorkerLoop(runtime, config=WorkerLoopConfig(poll_interval_seconds=0.01, recovery_interval_seconds=1))

    assert loop.run_once() is True
    assert runtime.recoveries == 1
    assert runtime.executions == 1
    assert loop.iterations == 1
    assert loop.last_error is None


def test_run_once_returns_false_when_queue_is_empty() -> None:
    runtime = FakeRuntime([])
    loop = WorkerLoop(runtime)

    assert loop.run_once() is False
    assert runtime.recoveries == 1
    assert runtime.executions == 1


def test_run_once_preserves_exception_for_direct_callers() -> None:
    runtime = FakeRuntime([], failures=1)
    loop = WorkerLoop(runtime)

    with pytest.raises(RuntimeError, match="temporary failure"):
        loop.run_once()

    assert "RuntimeError" in (loop.last_error or "")


def test_background_loop_survives_transient_failure() -> None:
    runtime = FakeRuntime([object()], failures=1)
    loop = WorkerLoop(
        runtime,
        config=WorkerLoopConfig(
            poll_interval_seconds=0.01,
            recovery_interval_seconds=0.01,
            error_backoff_seconds=0.01,
        ),
    )

    loop.start()
    deadline = time.monotonic() + 1.0
    while runtime.executions < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    loop.stop()

    assert runtime.executions >= 2
    assert loop.running is False
    assert loop.last_error is None


def test_start_is_idempotent_and_stop_is_safe() -> None:
    runtime = FakeRuntime([])
    loop = WorkerLoop(runtime, config=WorkerLoopConfig(poll_interval_seconds=0.01, recovery_interval_seconds=1))

    loop.start()
    first_thread = loop._thread
    loop.start()
    assert loop._thread is first_thread

    loop.stop()
    loop.stop()
    assert loop.running is False
