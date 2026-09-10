from __future__ import annotations

from ..application.ai_generation import AIGenerationPlanner
from ..domain.content import ContentBrief, ScenePlan, ShotPlan
from ..domain.jobs import GenerationJob, JobInput, JobType
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
        return [self._enqueue(job, JobType.SHOT, "shot", f"{scene_id}:shot:{int(shot.get('number', i))}", {"shot": shot, "scene": scene, "sceneJobId": job.id, "sceneNumber": job.input.parameters.get("sceneNumber"), "shotNumber": int(shot.get("number", i))}, 2) for i, shot in enumerate(shots, 1) if isinstance(shot, dict)]

    def _create_generation_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        shot_data = job.input.parameters.get("shot")
        scene_data = job.input.parameters.get("scene")
        if not isinstance(shot_data, dict) or not isinstance(scene_data, dict):
            return []
        brief_data = job.input.parameters.get("brief", {})
        if not isinstance(brief_data, dict):
            brief_data = {}
        brief = ContentBrief(
            topic=str(brief_data.get("topic", "")),
            language=str(brief_data.get("language", "en")),
            duration_seconds=int(brief_data.get("durationSeconds", brief_data.get("duration_seconds", 60))),
            style=str(brief_data.get("style", "cinematic")),
            audience=str(brief_data.get("audience", "general")),
            platform=str(brief_data.get("platform", "youtube")),
            aspect_ratio=str(brief_data.get("aspectRatio", brief_data.get("aspect_ratio", "16:9"))),
        )
        scene = ScenePlan(
            number=int(scene_data.get("number", job.input.parameters.get("sceneNumber", 1))),
            title=str(scene_data.get("title", "Scene")),
            duration_seconds=float(scene_data.get("duration_seconds", scene_data.get("durationSeconds", 5))),
            visual=str(scene_data.get("visual", "")),
            narration=str(scene_data.get("narration", "")),
            shots=[],
        )
        shot = ShotPlan(
            number=int(shot_data.get("number", job.input.parameters.get("shotNumber", 1))),
            prompt=str(shot_data.get("prompt", "")),
            duration_seconds=float(shot_data.get("duration_seconds", shot_data.get("durationSeconds", 5))),
            camera=str(shot_data.get("camera", "medium")),
            lighting=str(shot_data.get("lighting", "natural")),
            style=str(shot_data.get("style", brief.style)),
        )
        count = max(1, min(int(job.input.parameters.get("takeCount", 1)), 8))
        created: list[GenerationJob] = []
        for take in range(1, count + 1):
            for spec in (
                self.generation_planner.image(brief, scene, shot, take),
                self.generation_planner.video(brief, scene, shot, take),
            ):
                target = {JobType.IMAGE: "image", JobType.VIDEO: "video"}[spec.job_type]
                params = {"shot": shot_data, "scene": scene_data, "shotJobId": job.id, "shotNumber": shot.number, "takeCount": count, "takeNumber": take, "generationSpec": {"prompt": spec.prompt, "negative_prompt": spec.negative_prompt, "duration_seconds": spec.duration_seconds, "parameters": spec.parameters or {}}}
                created.append(self._enqueue(job, spec.job_type, target, f"{job.id}:{target}:take:{take}", params, 3))
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
