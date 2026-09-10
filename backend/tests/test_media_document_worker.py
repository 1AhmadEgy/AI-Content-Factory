from types import SimpleNamespace

from app.domain.jobs import JobType
from app.workers.media_document_worker import MediaDocumentWorker
from app.workers.registry import WorkerRegistry


def _job(**parameters):
    return SimpleNamespace(
        id="job-1",
        project_id="project-1",
        type=JobType.METADATA,
        input=SimpleNamespace(parameters=parameters, reference_asset_ids=[]),
    )


def test_subtitle_output_is_valid_webvtt():
    payload = MediaDocumentWorker._subtitle(_job(text="Hello world", end="00:00:03.500"))
    assert payload.decode("utf-8") == "WEBVTT\n\n00:00:00.000 --> 00:00:03.500\nHello world\n"


def test_metadata_output_is_deterministic_and_contains_publish_fields():
    payload = MediaDocumentWorker._metadata(_job(title="Launch", tags=["ai", "video"], language="ar", platforms=["youtube"]))
    assert payload.endswith(b"\n")
    text = payload.decode("utf-8")
    assert '"title": "Launch"' in text
    assert '"language": "ar"' in text
    assert '"platforms": ["youtube"]' in text


def test_registry_routes_media_jobs_to_media_document_worker():
    class HealthyWorker:
        worker_type = "media-document"

        def health_check(self):
            return True

    registry = WorkerRegistry()
    worker = HealthyWorker()
    registry.register(worker, capabilities={"SUBTITLE", "THUMBNAIL", "METADATA"}, worker_id="media-document")
    assert registry.resolve_for_job(JobType.THUMBNAIL) == "media-document"
    assert registry.resolve_for_job(JobType.SUBTITLE) == "media-document"
    assert registry.resolve_for_job(JobType.METADATA) == "media-document"
