"""The deterministic mock AI provider - classification and confidence bands."""

from __future__ import annotations

import pytest

from app.models.enums import Category, ConfidenceBand, MediaType, Platform, SourceType, TriggerType
from app.services.ai.mock import MockAIProvider
from app.services.intent import band_for
from app.services.media.normalized import NormalizedMedia


def _text_media(text: str, *, note: str | None = None) -> NormalizedMedia:
    return NormalizedMedia(
        source_type=SourceType.TEXT,
        platform=Platform.WEB,
        media_type=MediaType.TEXT,
        extracted_text=text,
        user_note=note,
    )


async def _analyze(text: str, *, note: str | None = None):
    result = await MockAIProvider().analyze(_text_media(text, note=note))
    return result.analysis


async def test_place_classified_high_confidence():
    analysis = await _analyze(
        "Amazing rooftop cafe and restaurant on MG Road, Bangalore. Great coffee "
        "and brunch spot, located near the beach - must visit this place."
    )
    assert analysis.category == Category.PLACE
    assert analysis.resurfacing.type == TriggerType.LOCATION
    assert band_for(analysis.confidence) == ConfidenceBand.HIGH
    assert analysis.why_saved.startswith("You probably saved this because")


async def test_event_detects_date_and_uses_date_trigger():
    analysis = await _analyze(
        "Coldplay concert live on 2026-09-14. Buy tickets for this show!"
    )
    assert analysis.category == Category.EVENT
    assert analysis.resurfacing.type == TriggerType.DATE
    assert analysis.details.date == "2026-09-14"


async def test_event_without_date_degrades_to_manual():
    analysis = await _analyze(
        "Some concert festival gig with a great lineup and tickets available."
    )
    assert analysis.category == Category.EVENT
    # No concrete date -> Echo does not invent one, falls back to a manual nudge.
    assert analysis.resurfacing.type == TriggerType.MANUAL


async def test_recipe_uses_time_trigger():
    analysis = await _analyze(
        "Creamy garlic butter pasta recipe. Preheat, simmer the sauce, serves 4. "
        "Cook this dish for dinner."
    )
    assert analysis.category == Category.RECIPE
    assert analysis.resurfacing.type == TriggerType.TIME


async def test_topic_medium_band():
    analysis = await _analyze("A nice article to read.")
    assert analysis.category == Category.TOPIC
    assert band_for(analysis.confidence) == ConfidenceBand.MEDIUM


async def test_thin_content_is_low_confidence():
    analysis = await _analyze("hmm ok")
    assert band_for(analysis.confidence) == ConfidenceBand.LOW
    assert analysis.uncertainty_note is not None


async def test_note_raises_confidence():
    without = await _analyze("A nice article to read.")
    with_note = await _analyze(
        "A nice article to read.", note="want to study this properly"
    )
    assert with_note.confidence > without.confidence


@pytest.mark.parametrize(
    "value,expected",
    [
        (0.95, ConfidenceBand.HIGH),
        (0.80, ConfidenceBand.HIGH),
        (0.79, ConfidenceBand.MEDIUM),
        (0.55, ConfidenceBand.MEDIUM),
        (0.54, ConfidenceBand.LOW),
        (0.1, ConfidenceBand.LOW),
    ],
)
def test_band_thresholds(value, expected):
    assert band_for(value) == expected
