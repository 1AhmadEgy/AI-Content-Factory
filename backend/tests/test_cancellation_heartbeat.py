import time

from app.orchestrator.cancellation import CancellationRegistry
from app.orchestrator.heartbeat import LeaseHeartbeat
from app.orchestrator.queue import JobLease


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
        def heartbeat(self, lease):
            calls.append(lease)

    lease = JobLease("job-1", "worker-1", "lease-1", "2099-01-01T00:00:00+00:00")
    heartbeat = LeaseHeartbeat(Queue(), lease, interval_seconds=0.01)
    heartbeat.start()
    time.sleep(0.035)
    heartbeat.stop()

    assert calls
    assert all(call == lease for call in calls)
