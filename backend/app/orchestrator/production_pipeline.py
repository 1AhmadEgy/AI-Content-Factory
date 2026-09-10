from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..application.language_media_service import LanguageMediaService
from ..domain.jobs import GenerationJob, JobStatus, JobType
from .content_pipeline import ContentPipelineOrchestrator
from .production_contract import build_production_context


class ProductionPipelineOrchestrator(ContentPipelineOrchestrator):
    """Production pipeline with immutable episode/language-media handoff."""

    def on_completed(self, job: GenerationJob) -> list[GenerationJob]:
        # Language renders finish with their own final QC. They must never feed back
        # into the source-language -> language-pack branch.
        if job.type is JobType.QC and job.input.parameters.get("finalQc") and job.input.parameters.get("languageRender"):
            return self._create_language_delivery_jobs(job)

        created = super().on_completed(job)
        if job.type is JobType.QC and job.input.parameters.get("finalQc"):
            language_job = self._create_language_pack_job(job)
            if language_job is not None:
                created.append(language_job)
        elif job.type is JobType.LANGUAGE_PACK:
            created.extend(self._create_language_media_jobs(job))
        elif job.type is JobType.QC and self._is_language_tts_qc(job):
            created.extend(self._create_lipsync_jobs(job))
            created.extend(self._maybe_create_language_timeline(job))
        elif job.type is JobType.SUBTITLE:
            created.extend(self._maybe_create_language_timeline(job))
        elif job.type is JobType.QC and self._is_language_lipsync_qc(job):
            created.extend(self._maybe_create_language_timeline(job))
        return created

    def _create_language_pack_job(self, final_qc_job: GenerationJob) -> GenerationJob | None:
        render_job_id = str(final_qc_job.input.parameters.get("sourceJobId", ""))
        render_job = self.job_service.repository.get(render_job_id) if render_job_id else None
        if render_job is None:
            return None

        root = render_job
        visited: set[str] = set()
        while root.parent_job_id and root.id not in visited:
            visited.add(root.id)
            parent = self.job_service.repository.get(root.parent_job_id)
            if parent is None:
                break
            root = parent

        parameters = root.input.parameters
        snapshot = parameters.get("episodeSnapshot")
        variants = parameters.get("languagePackVariants")
        if not isinstance(snapshot, dict) or not isinstance(variants, dict) or not variants:
            return None

        production_context = build_production_context(
            snapshot,
            country_id=str(parameters.get("countryId") or snapshot.get("countryId") or ""),
            library_id=str(parameters.get("libraryId") or snapshot.get("libraryId") or ""),
            source_language=str(parameters.get("sourceLanguage") or snapshot.get("sourceLanguage") or snapshot.get("language") or ""),
            target_languages=[str(x) for x in parameters.get("targetLanguages", list(variants.keys()))],
            dialect=parameters.get("dialect") or snapshot.get("dialect"),
            glossary=dict(parameters.get("glossary") or snapshot.get("glossary") or {}),
        )
        pack_parameters: dict[str, Any] = {
            "episodeId": production_context["episodeId"],
            "sourceLanguage": production_context["sourceLanguage"],
            "targetLanguages": production_context["targetLanguages"],
            "version": int(parameters.get("languagePackVersion", 1)),
            "source": deepcopy(production_context["episodeSnapshot"]),
            "variants": deepcopy(variants),
            "errors": list(parameters.get("languagePackErrors") or []),
            "productionContext": production_context,
        }
        return self._enqueue(
            final_qc_job,
            JobType.LANGUAGE_PACK,
            "language-pack",
            f"{root.id}:language-pack:{pack_parameters['version']}",
            pack_parameters,
            1,
            list(final_qc_job.output.asset_ids) if final_qc_job.output else [],
        )

    def _create_language_media_jobs(self, language_pack_job: GenerationJob) -> list[GenerationJob]:
        parameters = language_pack_job.input.parameters
        variants = parameters.get("variants")
        if not isinstance(variants, dict):
            return []
        version = int(parameters.get("version", 1))
        created: list[GenerationJob] = []
        snapshot = parameters.get("source") if isinstance(parameters.get("source"), dict) else {}
        snapshot_voices = self._character_voice_map(snapshot)
        for language, raw_variant in sorted(variants.items()):
            if not isinstance(raw_variant, dict):
                continue
            variant = deepcopy(raw_variant)
            variant["language"] = str(variant.get("language") or language)
            variant["sourceEpisodeId"] = parameters.get("episodeId")
            variant["languagePackVersion"] = version
            character_voices = dict(snapshot_voices)
            character_voices.update(dict(variant.get("characterVoices") or {}))
            variant["characterVoices"] = character_voices
            media_context = {
                "episodeId": parameters.get("episodeId"),
                "language": variant["language"],
                "locale": variant.get("locale"),
                "sourceLanguage": parameters.get("sourceLanguage"),
                "languagePackVersion": version,
                "sourcePreserved": True,
            }
            subtitle_parameters = {
                "language": variant["language"],
                "locale": variant.get("locale"),
                "episodeId": parameters.get("episodeId"),
                "languagePackVersion": version,
                "languagePackAssetId": (language_pack_job.output.asset_ids[0] if language_pack_job.output and language_pack_job.output.asset_ids else None),
                "languagePackVariant": variant,
                "mediaContext": media_context,
            }
            created.append(self._enqueue(
                language_pack_job,
                JobType.SUBTITLE,
                "subtitle",
                f"{language_pack_job.id}:subtitle:{language}:{version}",
                subtitle_parameters,
                1,
                list(language_pack_job.output.asset_ids) if language_pack_job.output else [],
            ))

            tts_manifest = LanguageMediaService.build_tts_manifest(variant)
            speech_units = tts_manifest["units"]
            if speech_units:
                tts_parameters = {
                    "language": variant["language"],
                    "locale": variant.get("locale"),
                    "episodeId": parameters.get("episodeId"),
                    "languagePackVersion": version,
                    "languagePackAssetId": (language_pack_job.output.asset_ids[0] if language_pack_job.output and language_pack_job.output.asset_ids else None),
                    "languagePackVariant": variant,
                    "speechUnits": speech_units,
                    "characterVoices": character_voices,
                    "sourcePreserved": True,
                    "generationSpec": {
                        "prompt": f"Synthesize the supplied speech units in locale {variant.get('locale') or variant['language']} with stable speaker/character mapping.",
                        "negative_prompt": "Do not translate, rewrite, reorder, merge, or invent speech units.",
                        "duration_seconds": self._duration_from_units(speech_units),
                        "parameters": {
                            "language": variant["language"],
                            "locale": variant.get("locale"),
                            "characterVoices": character_voices,
                            "speechUnits": speech_units,
                        },
                    },
                }
                created.append(self._enqueue(
                    language_pack_job,
                    JobType.TTS,
                    "tts",
                    f"{language_pack_job.id}:tts:{language}:{version}",
                    tts_parameters,
                    1,
                    list(language_pack_job.output.asset_ids) if language_pack_job.output else [],
                ))
        return created

    def _create_lipsync_jobs(self, tts_qc_job: GenerationJob) -> list[GenerationJob]:
        source_tts_id = str(tts_qc_job.input.parameters.get("sourceJobId", ""))
        tts_job = self.job_service.repository.get(source_tts_id) if source_tts_id else None
        if tts_job is None or tts_job.type is not JobType.TTS or not tts_job.output or not tts_job.output.asset_ids:
            return []
        units = tts_job.input.parameters.get("speechUnits") or []
        if not isinstance(units, list):
            return []
        grouped: dict[str, list[dict[str, Any]]] = {}
        for unit in units:
            if not isinstance(unit, dict) or not str(unit.get("text", "")).strip():
                continue
            key = str(unit.get("characterId") or unit.get("speaker") or "__narrator__")
            grouped.setdefault(key, []).append(dict(unit))
        if not grouped:
            return []
        video_asset = self._find_source_video_asset(tts_job)
        if not video_asset:
            return []
        voices = tts_job.input.parameters.get("characterVoices") or {}
        created: list[GenerationJob] = []
        for character_id, character_units in sorted(grouped.items()):
            voice = voices.get(character_id) if isinstance(voices, dict) else None
            if voice is None:
                speaker = character_units[0].get("speaker")
                voice = voices.get(str(speaker)) if isinstance(voices, dict) and speaker else None
            parameters = {
                "language": tts_job.input.parameters.get("language"),
                "locale": tts_job.input.parameters.get("locale"),
                "episodeId": tts_job.input.parameters.get("episodeId"),
                "languagePackVersion": tts_job.input.parameters.get("languagePackVersion"),
                "characterId": character_id,
                "voice": voice,
                "requiresStableVoice": True,
                "speechUnits": character_units,
                "sourceTtsJobId": tts_job.id,
                "sourceVideoAssetId": video_asset,
                "generationSpec": {
                    "prompt": "Apply lip synchronization for the supplied character speech units to the supplied source video while preserving identity, timing and shot references.",
                    "negative_prompt": "Do not change character identity, camera, scene, dialogue, language, order, timing, or invent facial motion outside the supplied speech units.",
                    "duration_seconds": self._duration_from_units(character_units),
                    "parameters": {
                        "language": tts_job.input.parameters.get("language"),
                        "locale": tts_job.input.parameters.get("locale"),
                        "characterId": character_id,
                        "voice": voice,
                        "speechUnits": character_units,
                        "sourceVideoAssetId": video_asset,
                    },
                },
            }
            created.append(self._enqueue(
                tts_qc_job,
                JobType.LIPSYNC,
                "lipsync",
                f"{tts_job.id}:lipsync:{character_id}",
                parameters,
                1,
                [video_asset, tts_job.output.asset_ids[0]],
            ))
        return created

    def _maybe_create_language_timeline(self, trigger_job: GenerationJob) -> list[GenerationJob]:
        language_pack = self._find_language_pack_ancestor(trigger_job)
        if language_pack is None:
            return []
        variants = language_pack.input.parameters.get("variants")
        if not isinstance(variants, dict):
            return []
        language = str(trigger_job.input.parameters.get("language") or "")
        if not language:
            variant = trigger_job.input.parameters.get("languagePackVariant")
            language = str((variant or {}).get("language") or "") if isinstance(variant, dict) else ""
        if not language:
            return []
        subtitle_jobs = [j for j in self.job_service.repository.list_by_parent(language_pack.id) if j.type is JobType.SUBTITLE and str(j.input.parameters.get("language")) == language]
        subtitle = next((j for j in subtitle_jobs if j.status is JobStatus.COMPLETED and j.output and j.output.asset_ids), None)
        tts_jobs = [j for j in self.job_service.repository.list_by_parent(language_pack.id) if j.type is JobType.TTS and str(j.input.parameters.get("language")) == language]
        completed_tts = [j for j in tts_jobs if j.status is JobStatus.COMPLETED and j.output and j.output.asset_ids]
        if len(completed_tts) < len(tts_jobs):
            return []
        if tts_jobs and not all(self.job_service.repository.list_by_parent(t.id) for t in completed_tts):
            return []

        audio_asset_ids: list[str] = []
        for tts in completed_tts:
            tts_qcs = [q for q in self.job_service.repository.list_by_parent(tts.id) if q.type is JobType.QC and q.status is JobStatus.COMPLETED]
            if not tts_qcs:
                return []
            for qc in tts_qcs:
                lips = [j for j in self.job_service.repository.list_by_parent(qc.id) if j.type is JobType.LIPSYNC]
                if lips:
                    completed_lips = [j for j in lips if j.status is JobStatus.COMPLETED and j.output and j.output.asset_ids]
                    if len(completed_lips) < len(lips):
                        return []
                    audio_asset_ids.extend(j.output.asset_ids[0] for j in completed_lips)
                else:
                    audio_asset_ids.extend(qc.output.asset_ids if qc.output else [])
        if not audio_asset_ids and not subtitle:
            return []
        video_asset = self._find_source_video_asset(language_pack)
        if not video_asset:
            return []
        if not subtitle:
            return []
        variant = next((v for k, v in variants.items() if str(k) == language and isinstance(v, dict)), {})
        duration = self._duration_from_units(LanguageMediaService.speech_units(variant))
        if duration <= 1:
            duration = self._duration_from_variant(variant)
        parameters = {
            "languageRender": True,
            "language": language,
            "locale": variant.get("locale") if isinstance(variant, dict) else None,
            "episodeId": language_pack.input.parameters.get("episodeId"),
            "languagePackVersion": language_pack.input.parameters.get("version", 1),
            "durationUs": max(int(duration * 1_000_000), 1),
            "videoAssetIds": [video_asset],
            "audioAssetIds": audio_asset_ids,
            "subtitleAssetId": subtitle.output.asset_ids[0],
            "subtitleJobId": subtitle.id,
            "sourceEpisodeId": language_pack.input.parameters.get("episodeId"),
            "productionContext": language_pack.input.parameters.get("productionContext", {}),
            "sourcePreserved": True,
        }
        return [self._enqueue(
            language_pack,
            JobType.TIMELINE,
            "language-timeline",
            f"{language_pack.id}:timeline:{language}:{parameters['languagePackVersion']}",
            parameters,
            1,
            [video_asset, *audio_asset_ids, subtitle.output.asset_ids[0]],
        )]

    def _create_render_job(self, job: GenerationJob) -> list[GenerationJob]:
        if not job.output or not job.output.asset_ids:
            return []
        parameters = {
            "resolution": job.input.parameters.get("resolution", "1080p"),
            "aspectRatio": job.input.parameters.get("aspectRatio", "16:9"),
            "fps": job.input.parameters.get("fps", 30),
        }
        for key in ("languageRender", "language", "locale", "episodeId", "languagePackVersion", "subtitleAssetId", "sourceEpisodeId", "productionContext", "sourcePreserved"):
            if key in job.input.parameters:
                parameters[key] = job.input.parameters[key]
        return [self._enqueue(job, JobType.RENDER, "render", f"{job.id}:render", parameters, 7, [job.output.asset_ids[0]])]

    def _create_final_qc_job(self, job: GenerationJob) -> list[GenerationJob]:
        if not job.output or not job.output.asset_ids:
            return []
        parameters = {"sourceJobId": job.id, "finalQc": True}
        for key in ("languageRender", "language", "locale", "episodeId", "languagePackVersion", "sourceEpisodeId", "productionContext", "sourcePreserved"):
            if key in job.input.parameters:
                parameters[key] = job.input.parameters[key]
        return [self._enqueue(job, JobType.QC, "final_qc", f"{job.id}:final-qc", parameters, 8, list(job.output.asset_ids))]

    def _create_language_delivery_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        if not job.input.reference_asset_ids:
            return []
        common = {
            "title": job.input.parameters.get("title", "AI Content"),
            "description": job.input.parameters.get("description", ""),
            "language": job.input.parameters.get("language", "en"),
            "locale": job.input.parameters.get("locale"),
            "languagePackVersion": job.input.parameters.get("languagePackVersion"),
            "episodeId": job.input.parameters.get("episodeId"),
            "sourceEpisodeId": job.input.parameters.get("sourceEpisodeId"),
            "platforms": job.input.parameters.get("platforms", ["youtube", "tiktok", "instagram", "facebook"]),
            "tags": job.input.parameters.get("tags", []),
            "languageRender": True,
        }
        ids = job.input.reference_asset_ids
        return [self._enqueue(job, t, target, f"{job.id}:{target}:language:{common['language']}", common, 1, ids) for t, target in ((JobType.SUBTITLE, "subtitle"), (JobType.THUMBNAIL, "thumbnail"), (JobType.METADATA, "metadata"), (JobType.PUBLISH, "publish"), (JobType.REPURPOSE, "repurpose"))]

    @staticmethod
    def _character_voice_map(snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        characters = snapshot.get("characters")
        if isinstance(characters, list):
            for character in characters:
                if not isinstance(character, dict):
                    continue
                character_id = character.get("id")
                voice = character.get("voice")
                if character_id and voice:
                    result[str(character_id)] = voice
        elif isinstance(characters, dict):
            for character_id, character in characters.items():
                if isinstance(character, dict) and character.get("voice"):
                    result[str(character_id)] = character["voice"]
        return result

    def _find_source_video_asset(self, job: GenerationJob) -> str | None:
        current = job
        visited: set[str] = set()
        while current and current.id not in visited:
            visited.add(current.id)
            if current.type is JobType.RENDER and current.status is JobStatus.COMPLETED and current.output and current.output.asset_ids:
                return current.output.asset_ids[0]
            if not current.parent_job_id:
                break
            current = self.job_service.repository.get(current.parent_job_id)
        return None

    def _find_language_pack_ancestor(self, job: GenerationJob) -> GenerationJob | None:
        current = job
        visited: set[str] = set()
        while current and current.id not in visited:
            visited.add(current.id)
            if current.type is JobType.LANGUAGE_PACK:
                return current
            if not current.parent_job_id:
                break
            current = self.job_service.repository.get(current.parent_job_id)
        return None

    def _is_language_tts_qc(self, job: GenerationJob) -> bool:
        source_id = str(job.input.parameters.get("sourceJobId", ""))
        source = self.job_service.repository.get(source_id) if source_id else None
        return bool(source and source.type is JobType.TTS and self._find_language_pack_ancestor(source))

    def _is_language_lipsync_qc(self, job: GenerationJob) -> bool:
        source_id = str(job.input.parameters.get("sourceJobId", ""))
        source = self.job_service.repository.get(source_id) if source_id else None
        return bool(source and source.type is JobType.LIPSYNC and self._find_language_pack_ancestor(source))

    @staticmethod
    def _duration_from_variant(variant: dict[str, Any]) -> float:
        for key in ("durationSeconds", "duration_seconds"):
            value = variant.get(key)
            if isinstance(value, (int, float)):
                return max(float(value), 1.0)
        return 1.0

    @staticmethod
    def _duration_from_units(units: list[dict[str, Any]]) -> float:
        def seconds(value: Any) -> float:
            if isinstance(value, (int, float)):
                return max(0.0, float(value))
            text = str(value or "").strip()
            if not text:
                return 0.0
            parts = text.split(":")
            try:
                if len(parts) == 3:
                    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                if len(parts) == 2:
                    return float(parts[0]) * 60 + float(parts[1])
                return float(text)
            except ValueError:
                return 0.0

        return max((seconds(unit.get("end")) for unit in units if isinstance(unit, dict)), default=1.0)
