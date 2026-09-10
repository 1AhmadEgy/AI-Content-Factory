from __future__ import annotations

from ..domain.jobs import GenerationJob, JobInput, JobType
from ..application.ai_generation import AIGenerationPlanner
from .job_service import JobService


class ContentPipelineOrchestrator:
    """Expand completed jobs through the complete offline-first production lifecycle."""

    def __init__(self, job_service: JobService, enqueue, generation_planner: AIGenerationPlanner | None = None) -> None:
        self.job_service = job_service
        self.enqueue = enqueue
        self.generation_planner = generation_planner or AIGenerationPlanner()

    def on_completed(self, job: GenerationJob) -> list[GenerationJob]:
        if job.type is JobType.STORY:
            return self._create_scene_jobs(job)
        if job.type is JobType.SCENE:
            return self._create_shot_jobs(job)
        if job.type is JobType.SHOT:
            return self._create_generation_jobs(job)
        if job.type in {JobType.IMAGE, JobType.VIDEO, JobType.TTS, JobType.LIPSYNC, JobType.MUSIC, JobType.SFX}:
            return self._create_qc_job(job)
        if job.type is JobType.QC:
            return self._create_delivery_jobs(job) if job.input.parameters.get("finalQc") else self._create_best_take_job(job)
        if job.type is JobType.BEST_TAKE:
            return self._create_timeline_job(job)
        if job.type is JobType.TIMELINE:
            return self._create_render_job(job)
        if job.type is JobType.RENDER:
            return self._create_final_qc_job(job)
        return []

    def _create_scene_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        plan = job.input.parameters.get("plan")
        scenes = plan.get("scenes", []) if isinstance(plan, dict) else []
        return [self._enqueue(job, JobType.SCENE, "scene", f"{job.id}:scene:{int(scene.get('number', i))}", {"scene": scene, "storyJobId": job.id, "sceneNumber": int(scene.get("number", i))}, 1) for i, scene in enumerate(scenes, 1) if isinstance(scene, dict)]

    def _create_shot_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        scene = job.input.parameters.get("scene")
        shots = scene.get("shots", []) if isinstance(scene, dict) else []
        scene_id = job.target_id or f"{job.id}:scene"
        return [self._enqueue(job, JobType.SHOT, "shot", f"{scene_id}:shot:{int(shot.get('number', i))}", {"shot": shot, "sceneJobId": job.id, "sceneNumber": job.input.parameters.get("sceneNumber"), "shotNumber": int(shot.get("number", i))}, 2) for i, shot in enumerate(shots, 1) if isinstance(shot, dict)]

    def _create_generation_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        shot = job.input.parameters.get("shot")
        if not isinstance(shot, dict):
            return []
        count = max(1, min(int(job.input.parameters.get("takeCount", 1)), 8))
        common = {"shot": shot, "shotJobId": job.id, "shotNumber": job.input.parameters.get("shotNumber"), "takeCount": count}
        created: list[GenerationJob] = []
        for job_type, target in ((JobType.IMAGE, "image"), (JobType.VIDEO, "video"), (JobType.TTS, "voice")):
            for take in range(1, count + 1):
                params = {**common, "takeNumber": take}
                created.append(self._enqueue(job, job_type, target, f"{job.id}:{target}:take:{take}", params, 3))
        return created

    def _create_qc_job(self, job: GenerationJob) -> list[GenerationJob]:
        if not job.output or not job.output.asset_ids:
            return []
        return [self._enqueue(job, JobType.QC, "qc", f"{job.id}:qc", {"sourceJobId": job.id, "takeNumber": job.input.parameters.get("takeNumber"), "takeCount": job.input.parameters.get("takeCount", 1)}, 4, list(job.output.asset_ids))]

    def _create_best_take_job(self, job: GenerationJob) -> list[GenerationJob]:
        if not job.input.reference_asset_ids:
            return []
        score = float(job.output.metrics.get("score", 0)) if job.output else 0.0
        candidates = [{"assetId": a, "score": score, "takeNumber": job.input.parameters.get("takeNumber")} for a in job.input.reference_asset_ids]
        return [self._enqueue(job, JobType.BEST_TAKE, "best_take", f"{job.id}:best-take", {"candidates": candidates, "qcJobId": job.id, "takeNumber": job.input.parameters.get("takeNumber")}, 5)]

    def _create_timeline_job(self, job: GenerationJob) -> list[GenerationJob]:
        if not job.output or not job.output.asset_ids:
            return []
        return [self._enqueue(job, JobType.TIMELINE, "timeline", f"{job.id}:timeline", {"sourceBestTakeJobId": job.id}, 6, [job.output.asset_ids[0]])]

    def _create_render_job(self, job: GenerationJob) -> list[GenerationJob]:
        if not job.output or not job.output.asset_ids:
            return []
        return [self._enqueue(job, JobType.RENDER, "render", f"{job.id}:render", {"resolution": job.input.parameters.get("resolution", "1080p"), "aspectRatio": job.input.parameters.get("aspectRatio", "16:9"), "fps": job.input.parameters.get("fps", 30)}, 7, [job.output.asset_ids[0]])]

    def _create_final_qc_job(self, job: GenerationJob) -> list[GenerationJob]:
        if not job.output or not job.output.asset_ids:
            return []
        return [self._enqueue(job, JobType.QC, "final_qc", f"{job.id}:final-qc", {"sourceJobId": job.id, "finalQc": True}, 8, list(job.output.asset_ids))]

    def _create_delivery_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        if not job.input.reference_asset_ids:
            return []
        common = {"title": job.input.parameters.get("title", "AI Content"), "description": job.input.parameters.get("description", ""), "language": job.input.parameters.get("language", "en"), "platforms": job.input.parameters.get("platforms", ["youtube", "tiktok", "instagram", "facebook"]), "tags": job.input.parameters.get("tags", [])}
        ids = job.input.reference_asset_ids
        return [self._enqueue(job, t, target, f"{job.id}:{target}", common, 1, ids) for t, target in ((JobType.SUBTITLE, "subtitle"), (JobType.THUMBNAIL, "thumbnail"), (JobType.METADATA, "metadata"), (JobType.PUBLISH, "publish"))]

    def _enqueue(self, parent: GenerationJob, job_type: JobType, target_type: str, target_id: str, parameters: dict[str, object], priority_offset: int, reference_asset_ids: list[str] | None = None) -> GenerationJob:
        child = self.job_service.create(project_id=parent.project_id, job_type=job_type, target_type=target_type, target_id=target_id, parent_job_id=parent.id, priority=max(parent.priority - priority_offset, 0), provider=parent.provider, model=parent.model, input=JobInput(parameters=parameters, reference_asset_ids=list(reference_asset_ids or []), deterministic=parent.input.deterministic))
        self.enqueue(child)
        return child
