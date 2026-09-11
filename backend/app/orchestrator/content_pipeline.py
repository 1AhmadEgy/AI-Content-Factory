from __future__ import annotations

import hashlib
import json

from ..application.ai_generation import AIGenerationPlanner
from ..domain.content import ContentBrief, ScenePlan, ShotPlan
from ..domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from .job_service import JobService


class ContentPipelineOrchestrator:
    """Expand jobs through the real production lifecycle without synthetic media."""

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
        if job.type in {JobType.IMAGE, JobType.TTS}:
            return self._create_qc_job(job)
        if job.type is JobType.QC:
            if job.input.parameters.get("finalQc"):
                return self._create_delivery_jobs(job)
            if job.input.parameters.get("auxiliary"):
                return self._maybe_create_timeline_for_scene(job)
            return self._maybe_create_best_take(job)
        if job.type is JobType.BEST_TAKE:
            return self._maybe_create_timeline_for_scene(job)
        if job.type is JobType.SUBTITLE:
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
        scene_data, brief_data = job.input.parameters.get("scene"), job.input.parameters.get("brief", {})
        if not isinstance(scene_data, dict) or not isinstance(brief_data, dict):
            return []
        brief = ContentBrief(topic=str(brief_data.get("topic", "")), language=str(brief_data.get("language", "en")), duration_seconds=int(brief_data.get("durationSeconds", 60)), style=str(brief_data.get("style", "cinematic")), audience=str(brief_data.get("audience", "general")), platform=str(brief_data.get("platform", "youtube")), aspect_ratio=str(brief_data.get("aspectRatio", "16:9")))
        scene = ScenePlan(number=int(scene_data.get("number", 1)), title=str(scene_data.get("title", "Scene")), duration_seconds=float(scene_data.get("durationSeconds", scene_data.get("duration_seconds", 5))), visual=str(scene_data.get("visual", "")), narration=str(scene_data.get("narration", "")), shots=[])
        if not scene.narration.strip():
            return []
        spec = self.generation_planner.tts(brief, scene)
        params = {"scene": scene_data, "brief": brief_data, "sceneJobId": job.id, "auxiliary": True, "generationSpec": {"prompt": spec.prompt, "negative_prompt": spec.negative_prompt, "duration_seconds": spec.duration_seconds, "parameters": spec.parameters or {}}}
        return [self._enqueue(job, spec.job_type, spec.job_type.value.lower(), f"{job.id}:{spec.job_type.value.lower()}", params, 2)]

    def _create_generation_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        shot_data = job.input.parameters.get("shot")
        if not isinstance(shot_data, dict):
            return []
        scene_data = job.input.parameters.get("scene")
        if not isinstance(scene_data, dict):
            scene_data = {"number": job.input.parameters.get("sceneNumber", 1), "title": "Scene", "durationSeconds": shot_data.get("durationSeconds", 5), "visual": shot_data.get("prompt", ""), "narration": ""}
        brief_data = job.input.parameters.get("brief", {})
        if not isinstance(brief_data, dict):
            brief_data = {}
        brief = ContentBrief(topic=str(brief_data.get("topic", "")), language=str(brief_data.get("language", "en")), duration_seconds=int(brief_data.get("durationSeconds", 60)), style=str(brief_data.get("style", "cinematic")), audience=str(brief_data.get("audience", "general")), platform=str(brief_data.get("platform", "youtube")), aspect_ratio=str(brief_data.get("aspectRatio", "16:9")))
        scene = ScenePlan(number=int(scene_data.get("number", 1)), title=str(scene_data.get("title", "Scene")), duration_seconds=float(scene_data.get("durationSeconds", 5)), visual=str(scene_data.get("visual", "")), narration=str(scene_data.get("narration", "")), shots=[])
        shot = ShotPlan(number=int(shot_data.get("number", 1)), prompt=str(shot_data.get("prompt", "")), duration_seconds=float(shot_data.get("durationSeconds", 5)), camera=str(shot_data.get("camera", "medium")), lighting=str(shot_data.get("lighting", "natural")), style=str(shot_data.get("style", brief.style)))
        count = max(1, min(int(job.input.parameters.get("takeCount", 4)), 8))
        created = []
        for take in range(1, count + 1):
            spec = self.generation_planner.image(brief, scene, shot, take)
            params = {"shot": shot_data, "scene": scene_data, "brief": brief_data, "shotJobId": job.id, "shotNumber": shot.number, "takeCount": count, "takeNumber": take, "takeGroupId": job.id, "generationSpec": {"prompt": spec.prompt, "negative_prompt": spec.negative_prompt, "duration_seconds": spec.duration_seconds, "parameters": spec.parameters or {}}}
            created.append(self._enqueue(job, JobType.IMAGE, "image", f"{job.id}:image:take:{take}", params, 3))
        return created

    def _create_qc_job(self, job: GenerationJob) -> list[GenerationJob]:
        if not job.output or not job.output.asset_ids:
            return []
        params = {"sourceJobId": job.id, "takeNumber": job.input.parameters.get("takeNumber"), "takeCount": job.input.parameters.get("takeCount", 1), "takeGroupId": job.input.parameters.get("takeGroupId"), "auxiliary": bool(job.input.parameters.get("auxiliary"))}
        return [self._enqueue(job, JobType.QC, "qc", f"{job.id}:qc", params, 4, list(job.output.asset_ids))]

    def _maybe_create_best_take(self, qc_job: GenerationJob) -> list[GenerationJob]:
        source_id = str(qc_job.input.parameters.get("sourceJobId", ""))
        source = self.job_service.repository.get(source_id) if source_id else None
        if source is None:
            return []
        shot_id = str(source.input.parameters.get("shotJobId", ""))
        shot = self.job_service.repository.get(shot_id) if shot_id else None
        if shot is None:
            return []
        generations = [j for j in self.job_service.repository.list_by_parent(shot.id) if j.type is JobType.IMAGE]
        expected = int(shot.input.parameters.get("takeCount", 1))
        if len(generations) < expected or any(j.status is not JobStatus.COMPLETED for j in generations):
            return []
        candidates = []
        for generation in generations:
            qc_jobs = [q for q in self.job_service.repository.list_by_parent(generation.id) if q.type is JobType.QC and q.status is JobStatus.COMPLETED and q.output and q.output.asset_ids]
            if not qc_jobs or not generation.output:
                continue
            score = float((qc_jobs[0].output.metrics if qc_jobs[0].output else {}).get("score", 0))
            candidates.extend({"assetId": asset_id, "score": score, "takeNumber": generation.input.parameters.get("takeNumber")} for asset_id in generation.output.asset_ids)
        if not candidates:
            return []
        return [self._enqueue(shot, JobType.BEST_TAKE, "best_take", f"{shot.id}:best-take", {"candidates": candidates, "shotJobId": shot.id, "takeCount": shot.input.parameters.get("takeCount", 1)}, 5)]

    def _maybe_create_timeline_for_scene(self, completed_job: GenerationJob) -> list[GenerationJob]:
        scene_id = str(completed_job.input.parameters.get("sceneJobId", ""))
        if not scene_id and completed_job.type is JobType.BEST_TAKE:
            shot = self.job_service.repository.get(str(completed_job.input.parameters.get("shotJobId", "")))
            scene_id = str(shot.parent_job_id) if shot else ""
        scene = self.job_service.repository.get(scene_id) if scene_id else None
        if scene is None:
            return []
        shots = [j for j in self.job_service.repository.list_by_parent(scene.id) if j.type is JobType.SHOT]
        best = [j for shot in shots for j in self.job_service.repository.list_by_parent(shot.id) if j.type is JobType.BEST_TAKE and j.status is JobStatus.COMPLETED and j.output and j.output.asset_ids]
        if not shots or len(best) < len(shots):
            return []

        audio_jobs = [j for j in self.job_service.repository.list_by_parent(scene.id) if j.type is JobType.TTS and j.input.parameters.get("auxiliary")]
        if any(j.status is not JobStatus.COMPLETED for j in audio_jobs):
            return []
        if not audio_jobs and str(scene.input.parameters.get("scene", {}).get("narration", "")).strip():
            return []

        scene_data = scene.input.parameters.get("scene")
        if not isinstance(scene_data, dict):
            return []
        narration = str(scene_data.get("narration", "")).strip()

        subtitle_jobs = [j for j in self.job_service.repository.list_by_parent(scene.id) if j.type is JobType.SUBTITLE and not j.input.parameters.get("finalDelivery")]
        subtitle = next((j for j in subtitle_jobs if j.status is JobStatus.COMPLETED and j.output and j.output.asset_ids), None)
        if narration and subtitle is None:
            duration = float(scene_data.get("durationSeconds", scene_data.get("duration_seconds", 5)) or 5)
            if duration <= 0 or not audio_jobs:
                return []
            audio = audio_jobs[0]
            if not audio.output or not audio.output.asset_ids:
                return []
            subtitle_parameters = {
                "language": str(scene.input.parameters.get("brief", {}).get("language", "en")),
                "text": narration,
                "end": duration,
                "sceneJobId": scene.id,
                "sourceTtsJobId": audio.id,
                "subtitleStage": "timeline_input",
            }
            self._enqueue(scene, JobType.SUBTITLE, "subtitle", f"{scene.id}:subtitle", subtitle_parameters, 5, [audio.output.asset_ids[0]])
            return []
        if narration and subtitle is None:
            return []

        image_ids: list[str] = []
        for best_job in best:
            selected = best_job.output.metrics.get("selectedAssetId") if best_job.output else None
            if not isinstance(selected, str) or not selected:
                return []
            image_ids.append(selected)

        audio_ids: list[str] = []
        for audio_job in audio_jobs:
            if not audio_job.output or not audio_job.output.asset_ids:
                return []
            audio_ids.extend(audio_job.output.asset_ids)

        try:
            duration_us = int(float(scene_data.get("durationSeconds", 5)) * 1_000_000)
        except (TypeError, ValueError, OverflowError):
            return []
        if duration_us <= 0:
            return []

        refs = [*image_ids, *audio_ids]
        parameters = {
            "durationUs": duration_us,
            "sceneJobId": scene.id,
            "videoAssetIds": image_ids,
            "audioAssetIds": audio_ids,
            "subtitleAssetId": subtitle.output.asset_ids[0] if subtitle else None,
            "sourceAssetTypes": ["IMAGE", "AUDIO"] + (["SUBTITLE"] if subtitle else []),
        }
        if subtitle:
            refs.append(subtitle.output.asset_ids[0])
        return [self._enqueue(scene, JobType.TIMELINE, "timeline", f"{scene.id}:timeline", parameters, 6, refs)]

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
        common = {"title": job.input.parameters.get("title", "AI Content"), "description": job.input.parameters.get("description", ""), "language": job.input.parameters.get("language", "en"), "platforms": job.input.parameters.get("platforms", []), "tags": job.input.parameters.get("tags", [])}
        ids = job.input.reference_asset_ids
        jobs = [self._enqueue(job, t, target, f"{job.id}:{target}", common, 1, ids) for t, target in ((JobType.SUBTITLE, "subtitle"), (JobType.THUMBNAIL, "thumbnail"), (JobType.METADATA, "metadata"), (JobType.REPURPOSE, "repurpose"))]
        if common["platforms"]:
            jobs.append(self._enqueue(job, JobType.PUBLISH, "publish", f"{job.id}:publish", common, 1, ids))
        return jobs

    def _enqueue(self, parent: GenerationJob, job_type: JobType, target_type: str, target_id: str, parameters: dict[str, object], priority_offset: int, reference_asset_ids: list[str] | None = None) -> GenerationJob:
        input_data = JobInput(parameters=parameters, reference_asset_ids=list(reference_asset_ids or []), deterministic=parent.input.deterministic)
        priority = max(parent.priority - priority_offset, 0)
        fingerprint_payload = {"parentJobId": parent.id, "projectId": parent.project_id, "jobType": job_type.value, "targetType": target_type, "targetId": target_id, "priority": priority, "provider": parent.provider, "model": parent.model, "input": {"parameters": parameters, "referenceAssetIds": input_data.reference_asset_ids, "deterministic": input_data.deterministic}}
        fingerprint = hashlib.sha256(json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
        key = f"pipeline:{parent.id}:{job_type.value}:{target_id}"
        result = self.job_service.create_with_idempotency(key=key, operation="pipeline_enqueue", fingerprint=fingerprint, project_id=parent.project_id, job_type=job_type, target_type=target_type, target_id=target_id, parent_job_id=parent.id, input=input_data, priority=priority, max_attempts=3, provider=parent.provider, model=parent.model)
        if result.conflict:
            raise ValueError(f"PIPELINE_IDEMPOTENCY_CONFLICT: {key}")
        if result.job is not None:
            self.enqueue(result.job)
            return result.job
        if result.existing_resource_id:
            existing = self.job_service.repository.get(result.existing_resource_id)
            if existing is not None:
                return existing
        raise RuntimeError(f"PIPELINE_IDEMPOTENCY_RESOURCE_MISSING: {key}")
