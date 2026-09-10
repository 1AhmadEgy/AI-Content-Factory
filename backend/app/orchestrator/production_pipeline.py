from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..domain.jobs import GenerationJob, JobType
from .content_pipeline import ContentPipelineOrchestrator
from .production_contract import build_production_context


class ProductionPipelineOrchestrator(ContentPipelineOrchestrator):
    """Production pipeline with immutable episode/language-pack handoff."""

    def on_completed(self, job: GenerationJob) -> list[GenerationJob]:
        created = super().on_completed(job)
        if job.type is JobType.QC and job.input.parameters.get("finalQc"):
            language_job = self._create_language_pack_job(job)
            if language_job is not None:
                created.append(language_job)
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
