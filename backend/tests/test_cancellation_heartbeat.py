import time

from backend.app.orchestrator.cancellation import CancellationRegistry
from backend.app.orchestrator.heartbeat import LeaseHeartbeat


def test_cancellation_registry_is_cooperative():
    registry = CancellationRegistry()
    assert registry.is_cancelled("job-1") is False
    registry.cancel("job-1")
    assert registry.is_cancelled("job-1") is True
    registry.clear("job-1")
    assert registry.is_cancelled("job-1") is False


def test_heartbeat_renews_lease():
    calls = []

    class Queue:
        def heartbeat(self, job_id, worker_id):
            calls.append((job_id, worker_id))
            return True

    heartbeat = LeaseHeartbeat(Queue(), "job-1", "worker-1", interval_seconds=0.01)
    heartbeat.start()
    time.sleep(0.035)
    heartbeat.stop()
    assert calls
    assert all(call == ("job-1", "worker-1") for call in calls)
