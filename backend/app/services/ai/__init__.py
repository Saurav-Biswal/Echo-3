"""AI provider selection.

``get_ai_provider`` honours ``settings.resolved_ai_provider()``, which returns
"mock" whenever no Gemini key is configured - so the app boots, tests run, and
the demo works with zero external dependencies (§40, §45).
"""

from __future__ import annotations

from app.config import settings
from app.services.ai.base import AIProvider, AnalysisResult
from app.services.ai.mock import MockAIProvider

_provider: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    global _provider
    if _provider is not None:
        return _provider

    resolved = settings.resolved_ai_provider()
    if resolved == "gemini":
        from app.services.ai.gemini import GeminiAIProvider

        _provider = GeminiAIProvider()
    else:
        _provider = MockAIProvider()
    return _provider


def reset_ai_provider() -> None:
    """Test hook: drop the cached provider so settings changes take effect."""
    global _provider
    _provider = None


__all__ = [
    "AIProvider",
    "AnalysisResult",
    "get_ai_provider",
    "reset_ai_provider",
]
