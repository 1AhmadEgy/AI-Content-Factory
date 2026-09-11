import json

from backend.app.application.ai_story_engine import AIStoryEngine
from backend.app.domain.content import ContentBrief
from backend.app.providers.builtin import LocalModelAdapter
from backend.app.providers.contracts import ProviderRequest
from backend.app.providers.registry import ModelRegistry, RegisteredModel


def test_story_engine_requires_real_provider_when_unconfigured() -> None:
    registry = ModelRegistry()
    try:
        AIStoryEngine(registry).generate(ContentBrief(topic="AI for beginners"))
        raise AssertionError("expected provider-unavailable error")
    except RuntimeError as exc:
        assert str(exc).startswith("AI_PROVIDER_UNAVAILABLE")


def test_local_adapter_parses_openai_compatible_response(monkeypatch) -> None:
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self):
            return json.dumps({"id": "run-1", "choices": [{"message": {"content": "hello"}}]}).encode()

    monkeypatch.setattr("backend.app.providers.builtin.urlopen", lambda *args, **kwargs: Response())
    adapter = LocalModelAdapter("http://localhost:11434", frozenset({"story"}))
    result = adapter.execute(ProviderRequest(model="test", parameters={"prompt": "hi"}))
    assert result.success is True
    assert result.output_text == "hello"
    assert result.provider_run_id == "run-1"


def test_story_engine_uses_provider_json() -> None:
    class Adapter(LocalModelAdapter):
        def __init__(self):
            super().__init__("http://unused", frozenset({"story"}))

        def execute(self, request):
            payload = {"title": "Generated", "logline": "A logline", "synopsis": "A synopsis", "scenes": [{
                "number": 1, "title": "Opening", "duration_seconds": 10, "visual": "Visual", "narration": "Narration",
                "shots": [{"number": 1, "prompt": "Shot", "duration_seconds": 10, "camera": "wide", "lighting": "soft", "style": "realistic", "character_ids": [], "location_ids": []}]
            }]}
            from backend.app.providers.contracts import ProviderResponse
            return ProviderResponse(True, output_text=json.dumps(payload), provider_run_id="run-real-contract")

    registry = ModelRegistry()
    registry.register(RegisteredModel("test-model", "test", Adapter(), priority=1))
    plan = AIStoryEngine(registry).generate(ContentBrief(topic="AI for beginners"), "test-model")
    assert plan.title == "Generated"
    assert len(plan.scenes) == 1
