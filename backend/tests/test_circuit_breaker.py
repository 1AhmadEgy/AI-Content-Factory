from __future__ import annotations

import threading
import time

import httpx

from app.infrastructure.error_classifier import ErrorKind, classify_exception, classify_provider_response
from app.infrastructure.resilience import CircuitState, SQLiteCircuitBreaker
from app.infrastructure.sqlite import SQLiteStore


def test_error_classification() -> None:
    request = httpx.Request("GET", "https://example.test")
    assert classify_exception(httpx.ReadTimeout("timeout")) is ErrorKind.TRANSIENT
    assert classify_exception(httpx.HTTPStatusError("429", request=request, response=httpx.Response(429, request=request))) is ErrorKind.TRANSIENT
    assert classify_exception(httpx.HTTPStatusError("400", request=request, response=httpx.Response(400, request=request))) is ErrorKind.PERMANENT
    assert classify_exception(httpx.HTTPStatusError("401", request=request, response=httpx.Response(401, request=request))) is ErrorKind.AUTH
    assert classify_provider_response("invalid_prompt", "bad prompt") is ErrorKind.PERMANENT
    assert classify_provider_response("rate_limit", "429") is ErrorKind.TRANSIENT


def test_circuit_opens_and_is_shared() -> None:
    store = SQLiteStore(":memory:")
    cb1 = SQLiteCircuitBreaker(store, "openai:model", fail_threshold=2, open_duration=10)
    cb2 = SQLiteCircuitBreaker(store, "openai:model", fail_threshold=2, open_duration=10)
    assert cb1.acquire()
    cb1.record_failure()
    assert cb2.acquire()
    cb2.record_failure()
    assert cb1.snapshot().state is CircuitState.OPEN
    assert not cb2.acquire()


def test_half_open_limits_concurrent_probes() -> None:
    store = SQLiteStore(":memory:")
    cb = SQLiteCircuitBreaker(store, "t1", fail_threshold=1, open_duration=0.05, half_open_max_calls=2, success_threshold=2)
    assert cb.acquire()
    cb.record_failure()
    time.sleep(0.08)
    results: list[bool] = []
    lock = threading.Lock()

    def attempt() -> None:
        value = cb.acquire()
        with lock:
            results.append(value)

    threads = [threading.Thread(target=attempt) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(results) == 2


def test_half_open_success_closes_and_failure_reopens() -> None:
    store = SQLiteStore(":memory:")
    cb = SQLiteCircuitBreaker(store, "t2", fail_threshold=2, open_duration=0.03, half_open_max_calls=2, success_threshold=2)
    assert cb.acquire()
    cb.record_failure()
    cb.record_failure()
    assert cb.snapshot().state is CircuitState.OPEN
    time.sleep(0.05)
    assert cb.acquire()
    assert cb.acquire()
    cb.record_success()
    cb.record_success()
    assert cb.snapshot().state is CircuitState.CLOSED
    assert cb.acquire()
    cb.record_failure()
    assert cb.snapshot().state is CircuitState.CLOSED
    cb.record_failure()
    assert cb.snapshot().state is CircuitState.OPEN
    assert not cb.acquire()
