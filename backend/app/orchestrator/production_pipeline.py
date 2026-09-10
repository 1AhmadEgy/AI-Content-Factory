from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..application.language_media_service import LanguageMediaService
from ..domain.jobs import GenerationJob, JobType
from .content_pipeline import ContentPipelineOrchestrator
from .production_contract import build_production_context


class ProductionPipelineOrchestrator(ContentPipelineOrchestrator):
    """Production pipeline with immutable episode/language-media handoff."""

    def on_completed(self, job: GenerationJob) -> list[GenerationJob]:
        created = super().on_completed(job)
        if job.type is JobType.QC and job.input.parameters.get("finalQc"):
            language_job = self._create_language_pack_job(job)
            if language_job is not None:
                created.append(language_job)
        elif job.type is JobType.LANGUAGE_PACK:
            created.extend(self._create_language_media_jobs(job))
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
        for language, raw_variant in sorted(variants.items()):
            if not isinstance(raw_variant, dict):
                continue
            variant = deepcopy(raw_variant)
            variant["language"] = str(variant.get("language") or language)
            variant["sourceEpisodeId"] = parameters.get("episodeId")
            variant["languagePackVersion"] = version
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
                    "sourcePreserved": True,
                    "generationSpec": {
                        "prompt": f"Synthesize the supplied speech units in locale {variant.get('locale') or variant['language']} with stable speaker/character mapping.",
                        "negative_prompt": "Do not translate, rewrite, reorder, merge, or invent speech units.",
                        "duration_seconds": self._duration_from_units(speech_units),
                        "parameters": {
                            "language": variant["language"],
                            "locale": variant.get("locale"),
                            "characterVoices": variant.get("characterVoices", {}),
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
