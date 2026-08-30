"""Intent orchestration - the decision layer above the raw AI call (§13, §42).

The provider returns an analysis; this service decides what Echo *does* with it:
which confidence band it falls in, and therefore whether the memory is saved
silently, saved with a confirm prompt, or routed to NEEDS_REVIEW for the user to
correct. Business logic reads bands, never raw floats, so the thresholds live in
one place.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.models import ConfidenceBand, MemoryStatus
from app.services.ai import AnalysisResult, get_ai_provider
from app.services.media.normalized import NormalizedMedia
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class IntentResult:
    """The analysis plus what Echo decided to do with it."""

    analysis: object  # IntentAnalysis, kept loose to avoid a schema import cycle
    model: str
    band: ConfidenceBand
    status: MemoryStatus
    needs_review: bool
    review_reason: str | None
    # True in the MEDIUM band: saved, but the client should ask "is this right?"
    wants_confirmation: bool


def band_for(confidence: float) -> ConfidenceBand:
    if confidence >= settings.confidence_high_threshold:
        return ConfidenceBand.HIGH
    if confidence >= settings.confidence_medium_threshold:
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW


class IntentService:
    def __init__(self, provider: object | None = None) -> None:
        self._provider = provider or get_ai_provider()

    async def analyze(self, media: NormalizedMedia) -> IntentResult:
        result: AnalysisResult = await self._provider.analyze(media)  # type: ignore[union-attr]
        analysis = result.analysis
        band = band_for(analysis.confidence)

        needs_review = band == ConfidenceBand.LOW
        status = MemoryStatus.NEEDS_REVIEW if needs_review else MemoryStatus.ACTIVE
        review_reason = None
        if needs_review:
            review_reason = (
                analysis.uncertainty_note
                or "Echo wasn't confident why you saved this."
            )

        logger.info(
            "intent.analyzed",
            model=result.model,
            category=analysis.category.value,
            confidence=analysis.confidence,
            band=band.value,
            needs_review=needs_review,
        )
        return IntentResult(
            analysis=analysis,
            model=result.model,
            band=band,
            status=status,
            needs_review=needs_review,
            review_reason=review_reason,
            wants_confirmation=band == ConfidenceBand.MEDIUM,
        )
