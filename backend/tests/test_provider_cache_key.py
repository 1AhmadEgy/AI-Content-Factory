from app.domain.jobs import GenerationJob, JobInput, JobType
from app.workers.provider_worker import ProviderGenerationWorker


def _job(*, target_id: str | None, parameters: dict, seed: int | None = None) -> GenerationJob:
    return GenerationJob(
        id="job-1",
        project_id="project-1",
        type=JobType.IMAGE,
        target_type="shot",
        target_id=target_id,
        input=JobInput(parameters=parameters, seed=seed),
    )


def test_cache_key_separates_different_targets() -> None:
    first = ProviderGenerationWorker._cache_key("provider", "model", _job(target_id="shot-1", parameters={"prompt": "same"}))
    second = ProviderGenerationWorker._cache_key("provider", "model", _job(target_id="shot-2", parameters={"prompt": "same"}))

    assert first != second


def test_cache_key_is_stable_for_equivalent_payloads() -> None:
    first = ProviderGenerationWorker._cache_key(
        "provider",
        "model",
        _job(target_id="shot-1", parameters={"b": 2, "a": 1}, seed=42),
    )
    second = ProviderGenerationWorker._cache_key(
        "provider",
        "model",
        _job(target_id="shot-1", parameters={"a": 1, "b": 2}, seed=42),
    )

    assert first == second


def test_cache_key_changes_when_seed_changes() -> None:
    first = ProviderGenerationWorker._cache_key("provider", "model", _job(target_id="shot-1", parameters={}, seed=1))
    second = ProviderGenerationWorker._cache_key("provider", "model", _job(target_id="shot-1", parameters={}, seed=2))

    assert first != second
