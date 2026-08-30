"""The AI provider interface.

Everything above this line speaks :class:`NormalizedMedia` in and
:class:`IntentAnalysis` out; nothing knows whether the answer came from Gemini
or from the deterministic mock. That is what lets the demo run offline and the
tests run without a key (§40, §45).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass

from app.schemas.ai_output import IntentAnalysis
from app.services.media.normalized import NormalizedMedia


@dataclass(slots=True)
class AnalysisResult:
    """One analysis plus the model that produced it (stored on the memory)."""

    analysis: IntentAnalysis
    model: str


class AIProvider(abc.ABC):
    """Turns normalised media into a validated intent analysis."""

    name: str = "base"

    @abc.abstractmethod
    async def analyze(self, media: NormalizedMedia) -> AnalysisResult:
        """Return the validated intent analysis for ``media``.

        Implementations raise :class:`app.utils.errors.AiError` (or a subclass)
        on failure, and :class:`MalformedAiOutputError` when the model's answer
        cannot be validated after repair.
        """
        raise NotImplementedError
