from types import SimpleNamespace

from app.domain.assets import AssetStatus, AssetType
from app.domain.jobs import JobType
from app.workers.repurpose_worker import RepurposeWorker


def test_repurpose_rejects_non_video_source():
    worker = RepurposeWorker.__new__(RepurposeWorker)
    worker._initialized = True
    worker.assets = SimpleNamespace(get=lambda _: SimpleNamespace(status=AssetStatus.READY, type=AssetType.IMAGE, path="/tmp/image.png"))
    worker.storage = None
    job = SimpleNamespace(
        type=JobType.REPURPOSE,
        input=SimpleNamespace(reference_asset_ids=["image-1"], parameters={}),
    )
    result = worker.execute(job, None)
    assert not result.success
    assert result.error_code == "REPURPOSE_SOURCE_NOT_VIDEO"


def test_repurpose_worker_declares_expected_type():
    assert RepurposeWorker.worker_type == "repurpose"
