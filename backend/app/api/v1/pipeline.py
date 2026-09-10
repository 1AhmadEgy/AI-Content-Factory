from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...application.pipeline import AssetCheckInput
from ...domain.best_take import TakeCandidate
from ...domain.timeline import Timeline
from ...orchestrator.pipeline_runner import PipelineRunner

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


class AssetInput(BaseModel):
    asset_id: str
    readable: bool = True
    size_bytes: int = Field(gt=0)
    license_status: str = "UNKNOWN"
    path: str | None = None


class CandidateInput(BaseModel):
    asset_id: str
    qc_score: float = Field(ge=0, le=1)
    semantic_score: float = Field(ge=0, le=1)
    continuity_score: float = Field(ge=0, le=1)
    technical_score: float = Field(ge=0, le=1)


class PipelineRequest(BaseModel):
    project_id: str
    assets: list[AssetInput]
    candidates: list[CandidateInput]
    duration_us: int = Field(gt=0)
    output_name: str = "mock-render.mp4"
    production: bool = True


@router.post("/run")
def run_pipeline(request: PipelineRequest) -> dict[str, object]:
    assets = [AssetCheckInput(**{key: value for key, value in item.model_dump().items() if key != "path"}) for item in request.assets]
    candidates = [TakeCandidate(**item.model_dump()) for item in request.candidates]
    timeline = Timeline(id=f"timeline-{request.project_id}", project_id=request.project_id, duration_us=request.duration_us)
    output = str(Path(gettempdir()) / "ai-content-factory" / request.output_name)
    asset_paths = {item.asset_id: item.path for item in request.assets if item.path}
    result = PipelineRunner(assets=asset_paths, production=request.production).run(
        assets=assets,
        candidates=candidates,
        timeline=timeline,
        output_path=output,
    )
    return {
        "qcPassed": result.qc_passed,
        "bestAssetId": result.best_asset_id,
        "renderedPath": result.rendered_path,
        "errors": result.errors,
    }
