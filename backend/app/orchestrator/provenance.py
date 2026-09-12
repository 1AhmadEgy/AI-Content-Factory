from __future__ import annotations

from ..domain.assets import Asset, AssetProvenance, LicenseStatus
from ..domain.jobs import GenerationJob


def build_provenance(
    job: GenerationJob,
    *,
    source_asset_ids: list[str] | None = None,
    metadata: dict[str, object] | None = None,
    license_status: LicenseStatus = LicenseStatus.UNKNOWN,
    provider: str | None = None,
    model: str | None = None,
) -> AssetProvenance:
    """Build a normalized provenance record for every produced asset.

    Provider-backed workers should pass the resolved provider/model explicitly so
    provenance reflects the adapter that actually produced the asset. Internal
    deterministic workers may identify themselves explicitly (for example,
    ``provider="internal"``) rather than fabricating an external AI provider.
    """
    resolved_provider = provider or getattr(job, "provider", None)
    resolved_model = model if model is not None else getattr(job, "model", None)
    if not resolved_provider:
        raise ValueError("PROVENANCE_PROVIDER_REQUIRED")

    input_data = job.input
    parameters = input_data.parameters
    return AssetProvenance(
        provider=resolved_provider,
        model=resolved_model,
        prompt=str(parameters.get("prompt", "")) or None,
        negative_prompt=str(parameters.get("negativePrompt", "")) or None,
        seed=input_data.seed,
        source_asset_ids=list(source_asset_ids or input_data.reference_asset_ids),
        job_id=job.id,
        license_status=license_status,
        metadata={
            "jobType": job.type.value,
            "targetType": job.target_type,
            "targetId": job.target_id,
            "parentJobId": getattr(job, "parent_job_id", None),
            **(metadata or {}),
        },
    )


def provenance_chain(asset: Asset, assets_by_id: dict[str, Asset]) -> list[str]:
    """Return the transitive asset lineage, oldest sources first."""
    result: list[str] = []
    visiting: set[str] = set()

    def visit(asset_id: str) -> None:
        if asset_id in visiting:
            raise ValueError("ASSET_PROVENANCE_CYCLE")
        current = assets_by_id.get(asset_id)
        if current is None or asset_id in result:
            return
        visiting.add(asset_id)
        for source_id in current.provenance.source_asset_ids:
            visit(source_id)
        visiting.remove(asset_id)
        result.append(asset_id)

    visit(asset.id)
    return result
