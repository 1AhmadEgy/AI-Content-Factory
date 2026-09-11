import pytest

from backend.app.application.ai_story_engine import AIStoryEngine
from backend.app.domain.content import ContentBrief
from backend.app.providers.registry import ModelRegistry


def test_ai_story_engine_requires_real_provider() -> None:
    with pytest.raises(RuntimeError, match="AI_PROVIDER_NOT_CONFIGURED:story"):
        AIStoryEngine(ModelRegistry()).generate(ContentBrief(topic="AI for beginners"))
