from __future__ import annotations

from ..application.ai_generation import AIGenerationPlanner
from ..domain.content import ContentBrief, ScenePlan, ShotPlan
from ..domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from .job_service import JobService


class ContentPipelineOrchestrator:
    """Expand jobs through the offline-first production lifecycle with sibling aggregation."""

    def __init__(self, job_service: JobService, enqueue, generation_planner: AIGenerationPlanner | None = None) -> None:
        self.job_service = job_service
        self.enqueue = enqueue
        self.generation_planner = generation_planner or AIGenerationPlanner()

    def on_completed(self, job: GenerationJob) -> list[GenerationJob]:
        if job.type is JobType.STORY:
            return self._create_scene_jobs(job)
        if job.type is JobType.SCENE:
            return self._create_shot_jobs(job) + self._create_audio_jobs(job)
        if job.type is JobType.SHOT:
            return self._create_generation_jobs(job)
        if job.type in {JobType.IMAGE, JobType.VIDEO, JobType.TTS, JobType.LIPSYNC, JobType.MUSIC, JobType.SFX}:
            return self._create_qc_job(job)
        if job.type is JobType.QC:
            if job.input.parameters.get("finalQc"):
                return self._create_delivery_jobs(job)
            if job.input.parameters.get("auxiliary"):
                return self._maybe_create_timeline_for_scene(job)
            return self._maybe_create_best_take(job)
        if job.type is JobType.BEST_TAKE:
            return self._maybe_create_timeline_for_scene(job)
        if job.type is JobType.TIMELINE:
            return self._create_render_job(job)
        if job.type is JobType.RENDER:
            return self._create_final_qc_job(job)
        return []

    def _create_scene_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        plan = job.input.parameters.get("plan")
        scenes = plan.get("scenes", []) if isinstance(plan, dict) else []
        brief = {k: job.input.parameters[k] for k in ("topic", "language", "durationSeconds", "style", "audience", "platform", "aspectRatio") if k in job.input.parameters}
        return [self._enqueue(job, JobType.SCENE, "scene", f"{job.id}:scene:{int(scene.get('number', i))}", {"scene": scene, "brief": brief, "storyJobId": job.id, "sceneNumber": int(scene.get("number", i))}, 1) for i, scene in enumerate(scenes, 1) if isinstance(scene, dict)]

    def _create_shot_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        scene = job.input.parameters.get("scene")
        shots = scene.get("shots", []) if isinstance(scene, dict) else []
        scene_id = job.target_id or f"{job.id}:scene"
        return [self._enqueue(job, JobType.SHOT, "shot", f"{scene_id}:shot:{int(shot.get('number', i))}", {"shot": shot, "scene": scene, "brief": job.input.parameters.get("brief", {}), "sceneJobId": job.id, "sceneNumber": job.input.parameters.get("sceneNumber"), "shotNumber": int(shot.get("number", i)), "takeCount": job.input.parameters.get("takeCount", 4)}, 2) for i, shot in enumerate(shots, 1) if isinstance(shot, dict)]

    def _create_audio_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        scene_data = job.input.parameters.get("scene")
        brief_data = job.input.parameters.get("brief", {})
        if not isinstance(scene_data, dict) or not isinstance(brief_data, dict):
            return []
        brief = ContentBrief(topic=str(brief_data.get("topic", "")), language=str(brief_data.get("language", "en")), duration_seconds=int(brief_data.get("durationSeconds", 60)), style=str(brief_data.get("style", "cinematic")), audience=str(brief_data.get("audience", "general")), platform=str(brief_data.get("platform", "youtube")), aspect_ratio=str(brief_data.get("aspectRatio", "16:9")))
        scene = ScenePlan(number=int(scene_data.get("number", 1)), title=str(scene_data.get("title", "Scene")), duration_seconds=float(scene_data.get("durationSeconds", scene_data.get("duration_seconds", 5))), visual=str(scene_data.get("visual", "")), narration=str(scene_data.get("narration", "")), shots=[])
        created = []
        for spec in (self.generation_planner.tts(brief, scene), self.generation_planner.audio(brief, scene, "music"), self.generation_planner.audio(brief, scene, "sfx")):
            params = {"scene": scene_data, "brief": brief_data, "sceneJobId": job.id, "auxiliary": True, "generationSpec": {"prompt": spec.prompt, "negative_prompt": spec.negative_prompt, "duration_seconds": spec.duration_seconds, "parameters": spec.parameters or {}}}
            created.append(self._enqueue(job, spec.job_type, spec.job_type.value.lower(), f"{job.id}:{spec.job_type.value.lower()}", params, 2))
        return created

    def _create_generation_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        shot_data, scene_data = job.input.parameters.get("shot"), job.input.parameters.get("scene")
        if not isinstance(shot_data, dict) or not isinstance(scene_data, dict): return []
        brief_data = job.input.parameters.get("brief", {})
        if not isinstance(brief_data, dict): brief_data = {}
        brief = ContentBrief(topic=str(brief_data.get("topic", "")), language=str(brief_data.get("language", "en")), duration_seconds=int(brief_data.get("durationSeconds", 60)), style=str(brief_data.get("style", "cinematic")), audience=str(brief_data.get("audience", "general")), platform=str(brief_data.get("platform", "youtube")), aspect_ratio=str(brief_data.get("aspectRatio", "16:9")))
        scene = ScenePlan(number=int(scene_data.get("number", 1)), title=str(scene_data.get("title", "Scene")), duration_seconds=float(scene_data.get("durationSeconds", 5)), visual=str(scene_data.get("visual", "")), narration=str(scene_data.get("narration", "")), shots=[])
        shot = ShotPlan(number=int(shot_data.get("number", 1)), prompt=str(shot_data.get("prompt", "")), duration_seconds=float(shot_data.get("durationSeconds", 5)), camera=str(shot_data.get("camera", "medium")), lighting=str(shot_data.get("lighting", "natural")), style=str(shot_data.get("style", brief.style)))
        count = max(1, min(int(job.input.parameters.get("takeCount", 4)), 8))
        created = []
        for take in range(1, count + 1):
            for spec in (self.generation_planner.image(brief, scene, shot, take), self.generation_planner.video(brief, scene, shot, take)):
                target = "image" if spec.job_type is JobType.IMAGE else "video"
                params = {"shot": shot_data, "scene": scene_data, "brief": brief_data, "shotJobId": job.id, "shotNumber": shot.number, "takeCount": count, "takeNumber": take, "takeGroupId": job.id, "generationSpec": {"prompt": spec.prompt, "negative_prompt": spec.negative_prompt, "duration_seconds": spec.duration_seconds, "parameters": spec.parameters or {}}}
                created.append(self._enqueue(job, spec.job_type, target, f"{job.id}:{target}:take:{take}", params, 3))
        return created

    def _create_qc_job(self, job: GenerationJob) -> list[GenerationJob]:
        if not job.output or not job.output.asset_ids: return []
        params = {"sourceJobId": job.id, "takeNumber": job.input.parameters.get("takeNumber"), "takeCount": job.input.parameters.get("takeCount", 1), "takeGroupId": job.input.parameters.get("takeGroupId"), "auxiliary": bool(job.input.parameters.get("auxiliary"))}
        return [self._enqueue(job, JobType.QC, "qc", f"{job.id}:qc", params, 4, list(job.output.asset_ids))]

    def _maybe_create_best_take(self, qc_job: GenerationJob) -> list[GenerationJob]:
        source_id = str(qc_job.input.parameters.get("sourceJobId", ""))
        source = self.job_service.repository.get(source_id) if source_id else None
        if source is None: return []
        shot_id = str(source.input.parameters.get("shotJobId", ""))
        shot = self.job_service.repository.get(shot_id) if shot_id else None
        if shot is None: return []
        generations = [j for j in self.job_service.repository.list_by_parent(shot.id) if j.type in {JobType.IMAGE, JobType.VIDEO}]
        expected = int(shot.input.parameters.get("takeCount", 1)) * 2
        if len(generations) < expected or any(j.status is not JobStatus.COMPLETED for j in generations): return []
        videos = [(g, q) for g in generations if g.type is JobType.VIDEO for q in self.job_service.repository.list_by_parent(g.id) if q.type is JobType.QC and q.status is JobStatus.COMPLETED and q.output and q.output.asset_ids]
        if len(videos) < int(shot.input.parameters.get("takeCount", 1)): return []
        existing = [j for j in self.job_service.repository.list_by_parent(shot.id) if j.type is JobType.BEST_TAKE]
        if existing: return []
        candidates = []
        for generation, qc in videos:
            score = float((qc.output.metrics if qc.output else {}).get("score", (generation.output.metrics if generation.output else {}).get("score", 0)))
            candidates.extend({"assetId": asset_id, "score": score, "takeNumber": generation.input.parameters.get("takeNumber")} for asset_id in generation.output.asset_ids if generation.output)
        if not candidates: return []
        return [self._enqueue(shot, JobType.BEST_TAKE, "best_take", f"{shot.id}:best-take", {"candidates": candidates, "shotJobId": shot.id, "takeCount": shot.input.parameters.get("takeCount", 1)}, 5)]

    def _maybe_create_timeline_for_scene(self, completed_job: GenerationJob) -> list[GenerationJob]:
        scene_id = str(completed_job.input.parameters.get("sceneJobId", ""))
        if not scene_id and completed_job.type is JobType.BEST_TAKE:
            shot = self.job_service.repository.get(str(completed_job.input.parameters.get("shotJobId", "")))
            scene_id = str(shot.parent_job_id) if shot else ""
        scene = self.job_service.repository.get(scene_id) if scene_id else None
        if scene is None: return []
        shots = [j for j in self.job_service.repository.list_by_parent(scene.id) if j.type is JobType.SHOT]
        best = [j for shot in shots for j in self.job_service.repository.list_by_parent(shot.id) if j.type is JobType.BEST_TAKE and j.status is JobStatus.COMPLETED and j.output and j.output.asset_ids]
        if not shots or len(best) < len(shots): return []
        audio_qcs = [j for a in self.job_service.repository.list_by_parent(scene.id) if a.type in {JobType.TTS, JobType.MUSIC, JobType.SFX} for j in self.job_service.repository.list_by_parent(a.id) if j.type is JobType.QC and j.status is JobStatus.COMPLETED and j.output and j.output.asset_ids]
        existing = [j for j in self.job_service.repository.list_by_parent(scene.id) if j.type is JobType.TIMELINE]
        if existing: return []
        refs = [j.output.asset_ids[0] for j in best]
        refs.extend(j.output.asset_ids[0] for j in audio_qcs)
        duration_us = int(float(scene.input.parameters.get("scene", {}).get("durationSeconds", 5)) * 1_000_000)
        return [self._enqueue(scene, JobType.TIMELINE, "timeline", f"{scene.id}:timeline", {"durationUs": duration_us, "sceneJobId": scene.id}, 6, refs)]

    def _create_render_job(self, job: GenerationJob) -> list[GenerationJob]:
        if not job.output or not job.output.asset_ids: return []
        return [self._enqueue(job, JobType.RENDER, "render", f"{job.id}:render", {"resolution": job.input.parameters.get("resolution", "1080p"), "aspectRatio": job.input.parameters.get("aspectRatio", "16:9"), "fps": job.input.parameters.get("fps", 30)}, 7, [job.output.asset_ids[0]])]

    def _create_final_qc_job(self, job: GenerationJob) -> list[GenerationJob]:
        if not job.output or not job.output.asset_ids: return []
        return [self._enqueue(job, JobType.QC, "final_qc", f"{job.id}:final-qc", {"sourceJobId": job.id, "finalQc": True}, 8, list(job.output.asset_ids))]

    def _create_delivery_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        if not job.input.reference_asset_ids: return []
        common = {"title": job.input.parameters.get("title", "AI Content"), "description": job.input.parameters.get("description", ""), "language": job.input.parameters.get("language", "en"), "platforms": job.input.parameters.get("platforms", ["youtube", "tiktok", "instagram", "facebook"]), "tags": job.input.parameters.get("tags", [])}
        ids = job.input.reference_asset_ids
        return [self._enqueue(job, t, target, f"{job.id}:{target}", common, 1, ids) for t, target in ((JobType.SUBTITLE, "subtitle"), (JobType.THUMBNAIL, "thumbnail"), (JobType.METADATA, "metadata"), (JobType.PUBLISH, "publish"), (JobType.REPURPOSE, "repurpose"))]

    def _enqueue(self, parent: GenerationJob, job_type: JobType, target_type: str, target_id: str, parameters: dict[str, object], priority_offset: int, reference_asset_ids: list[str] | None = None) -> GenerationJob:
        child = self.job_service.create(project_id=parent.project_id, job_type=job_type, target_type=target_type, target_id=target_id, parent_job_id=parent.id, priority=max(parent.priority - priority_offset, 0), provider=parent.provider, model=parent.model, input=JobInput(parameters=parameters, reference_asset_ids=list(reference_asset_ids or []), deterministic=parent.input.deterministic))
        self.enqueue(child)
        return child
