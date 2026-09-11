import json

import pytest

from backend.app.application.ai_story_engine import AIStoryEngine
from backend.app.domain.content import ContentBrief
from backend.app.providers.builtin import LocalModelAdapter
from backend.app.providers.registry import ModelRegistry


def test_ai_story_engine_requires_real_provider() -> None:
    with pytest.raises(RuntimeError, match="AI_PROVIDER_NOT_CONFIGURED:story"):
        AIStoryEngine(ModelRegistry()).generate(ContentBrief(topic="AI for beginners"))


def test_local_adapter_parses_openai_compatible_response(monkeypatch) -> None:
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self):
            return json.dumps({"id": "run-1", "choices": [{"message": {"content": "hello"}}]}).encode()

    monkeypatch.setattr("backend.app.providers.builtin.urlopen", lambda *args, **kwargs: Response())
    adapter = LocalModelAdapter("http://localhost:11434", frozenset({"story"}))
    from backend.app.providers.contracts import ProviderRequest

    result = adapter.execute(ProviderRequest(model="test", parameters={"prompt": "hi"}))
    assert result.success is True
    assert result.output_text == "hello"
    assert result.provider_run_id == "run-1"
