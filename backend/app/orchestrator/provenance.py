from __future__ import annotations

from ..domain.assets import Asset, AssetProvenance, LicenseStatus
from ..domain.jobs import GenerationJob


def build_provenance(
    job: GenerationJob,
    *,
    source_asset_ids: list[str] | None = None,
    metadata: dict[str, object] | None = None,
    license_status: LicenseStatus = LicenseStatus.UNKNOWN,
) -> AssetProvenance:
    """Build a normalized provenance record for every produced asset."""
    metadata_value = dict(metadata or {})
    model = getattr(job, "model", None) or (str(metadata_value["model"]) if metadata_value.get("model") else None)
    input_data = getattr(job, "input", None)
    parameters = getattr(input_data, "parameters", {}) or {}
    reference_asset_ids = getattr(input_data, "reference_asset_ids", []) or []
    return AssetProvenance(
        provider=getattr(job, "provider", None) or "mock",
        model=model,
        prompt=str(parameters.get("prompt", "")) or None,
        negative_prompt=str(parameters.get("negativePrompt", parameters.get("negative_prompt", ""))) or None,
        seed=getattr(input_data, "seed", None),
        source_asset_ids=list(source_asset_ids or reference_asset_ids),
        job_id=job.id,
        license_status=license_status,
        metadata={
            "jobType": job.type.value,
            "targetType": getattr(job, "target_type", None),
            "targetId": getattr(job, "target_id", None),
            "parentJobId": getattr(job, "parent_job_id", None),
            **metadata_value,
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
