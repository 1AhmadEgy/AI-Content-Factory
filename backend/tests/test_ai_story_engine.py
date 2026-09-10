import json

from backend.app.application.ai_story_engine import AIStoryEngine
from backend.app.domain.content import ContentBrief
from backend.app.providers.builtin import LocalModelAdapter, MockModelAdapter
from backend.app.providers.registry import ModelRegistry, RegisteredModel


def test_ai_story_engine_falls_back_to_deterministic_when_provider_has_no_text() -> None:
    registry = ModelRegistry()
    registry.register(RegisteredModel("mock", "mock", MockModelAdapter(), priority=1))
    plan = AIStoryEngine(registry).generate(ContentBrief(topic="AI for beginners"))
    assert plan.title == "AI for beginners"
    assert len(plan.scenes) > 0


def test_local_adapter_parses_openai_compatible_response(monkeypatch) -> None:
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self):
            return json.dumps({"id": "run-1", "choices": [{"message": {"content": "hello"}}]}).encode()

    monkeypatch.setattr("backend.app.providers.builtin.urlopen", lambda *args, **kwargs: Response())
    adapter = LocalModelAdapter("http://localhost:11434", frozenset({"story"}))
    result = adapter.execute(__import__("backend.app.providers.contracts", fromlist=["ProviderRequest"]).ProviderRequest(model="test", parameters={"prompt": "hi"}))
    assert result.success is True
    assert result.output_text == "hello"
    assert result.provider_run_id == "run-1"
