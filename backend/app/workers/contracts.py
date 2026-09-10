"""Backward-compatible worker contract aliases.

The orchestrator queue owns the canonical worker lifecycle contract.  Keeping
aliases here prevents the historical duplicate contract from drifting away
from the runtime implementation.
"""

from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext

WorkerResult = JobExecutionResult

__all__ = ["Worker", "WorkerContext", "WorkerResult", "JobExecutionResult"]
