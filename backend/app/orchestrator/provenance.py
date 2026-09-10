from __future__ import annotations

from ..domain.assets import Asset, AssetProvenance, LicenseStatus
from ..domain.jobs import GenerationJob


def build_provenance(job: GenerationJob, *, source_asset_ids: list[str] | None = None, metadata: dict[str, object] | None = None) -> AssetProvenance:
    """Build a normalized provenance record for every produced asset."""
    return AssetProvenance(
        provider=job.provider,
        model=job.model,
        prompt=str(job.input.parameters.get("prompt", "")) or None,
        negative_prompt=str(job.input.parameters.get("negativePrompt", "")) or None,
        seed=job.input.seed,
        source_asset_ids=list(source_asset_ids or job.input.reference_asset_ids),
        job_id=job.id,
        license_status=LicenseStatus.UNKNOWN,
        metadata={
            "jobType": job.type.value,
            "targetType": job.target_type,
            "targetId": job.target_id,
            "parentJobId": job.parent_job_id,
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
