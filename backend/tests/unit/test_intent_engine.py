"""Phase 1 intent-engine contract tests (§9).

These exercise the *content-understanding* half of the engine through the
deterministic mock provider: category, extracted facts (date/time/location/
address/price/url/duration), the source-vs-inference provenance flags, and the
hard rule that nothing is ever hallucinated. The mock stands in for Gemini here
because it implements the identical `IntentAnalysis` contract, so an assertion
that holds for the mock is an assertion about the shape every provider must
honour.
"""

from __future__ import annotations

from app.models.enums import (
    Category,
    ConfidenceBand,
    IntentAction,
    MediaType,
    Platform,
    SourceType,
    TriggerType,
)
from app.services.ai.mock import MockAIProvider
from app.services.intent import band_for
from app.services.media.normalized import NormalizedMedia


def _media(
    text: str,
    *,
    note: str | None = None,
    source_type: SourceType = SourceType.TEXT,
    platform: Platform = Platform.WEB,
    media_type: MediaType = MediaType.TEXT,
) -> NormalizedMedia:
    return NormalizedMedia(
        source_type=source_type,
        platform=platform,
        media_type=media_type,
        extracted_text=text,
        user_note=note,
    )


async def _analyze(text: str, **kwargs):
    result = await MockAIProvider().analyze(_media(text, **kwargs))
    return result.analysis


# --------------------------------------------------------------- categories


async def test_place_category_and_action():
    analysis = await _analyze(
        "Cosy rooftop cafe on Brigade Road, Bangalore. Perfect brunch spot to visit."
    )
    assert analysis.category == Category.PLACE
    assert analysis.intent_action == IntentAction.VISIT
    assert analysis.resurfacing.type == TriggerType.LOCATION


async def test_event_category_and_action():
    analysis = await _analyze(
        "Music festival concert with a stacked lineup. Tickets and RSVP open now."
    )
    assert analysis.category == Category.EVENT
    assert analysis.intent_action == IntentAction.ATTEND


async def test_recipe_category_and_action():
    analysis = await _analyze(
        "Garlic butter pasta recipe: preheat, simmer the sauce, add two tablespoons "
        "of cream. Serves 4. A dish to cook this week."
    )
    assert analysis.category == Category.RECIPE
    assert analysis.intent_action == IntentAction.COOK
    assert analysis.resurfacing.type == TriggerType.TIME


async def test_tool_category_and_action():
    analysis = await _analyze(
        "A handy productivity app - a SaaS tool with a browser extension. "
        "Install it and try the free features."
    )
    assert analysis.category == Category.TOOL
    assert analysis.intent_action == IntentAction.TRY
    assert analysis.resurfacing.type == TriggerType.MANUAL


async def test_topic_category_and_action():
    analysis = await _analyze(
        "A long-form article explaining the history and philosophy behind the idea. "
        "A guide worth a proper read."
    )
    assert analysis.category == Category.TOPIC
    assert analysis.intent_action == IntentAction.READ
    assert analysis.resurfacing.type == TriggerType.MANUAL


# --------------------------------------------------------------- extraction


async def test_date_extraction_iso():
    analysis = await _analyze("Big concert festival happening live on 2026-09-14. Tickets now.")
    assert analysis.details.date == "2026-09-14"
    assert analysis.provenance.date_stated is True
    assert analysis.resurfacing.type == TriggerType.DATE
    assert analysis.resurfacing.fire_at == "2026-09-14T09:00:00"


async def test_date_extraction_natural_language():
    analysis = await _analyze(
        "Summit conference and screening event on September 15, 2026. Grab tickets."
    )
    assert analysis.details.date == "2026-09-15"
    assert analysis.provenance.date_stated is True


async def test_time_extraction():
    analysis = await _analyze(
        "Live concert event on 2026-09-14, doors open 7:30 pm. Tickets available."
    )
    assert analysis.details.time == "19:30"
    assert analysis.provenance.time_stated is True
    assert analysis.resurfacing.fire_at == "2026-09-14T19:30:00"


async def test_location_extraction():
    analysis = await _analyze(
        "Great little cafe and bar located in Mumbai. Rooftop coffee spot to visit."
    )
    assert analysis.details.location == "Mumbai"
    assert analysis.provenance.location_stated is True


async def test_address_extraction():
    analysis = await _analyze(
        "New bistro on Linking Road, Mumbai - a brunch place worth a visit."
    )
    assert analysis.details.address == "Linking Road"
    assert analysis.provenance.address_stated is True


async def test_price_extraction():
    analysis = await _analyze(
        "Neat little SaaS app and tool. Subscription is $12 a month - install to try it."
    )
    assert analysis.details.price is not None
    assert "12" in analysis.details.price
    assert analysis.provenance.price_stated is True


async def test_url_extraction():
    analysis = await _analyze(
        "Must-read article and guide, full write-up at https://example.com/post here."
    )
    assert "https://example.com/post" in analysis.details.urls
    assert analysis.details.url == "https://example.com/post"
    assert analysis.provenance.url_stated is True


async def test_recipe_duration_extraction():
    analysis = await _analyze(
        "Quick pasta recipe: simmer the sauce and cook the dish in about 25 minutes. Serves 2."
    )
    primary = analysis.entities.for_category(Category.RECIPE)[0]
    assert primary.duration_minutes == 25


# ----------------------------------------------------- missing data / null


async def test_missing_facts_are_null_not_invented():
    """A bare topic states no date, place, price or coordinate - every one of
    those must come back null with its provenance flag false (§9)."""
    analysis = await _analyze("A nice article to read about an interesting idea.")
    d = analysis.details
    assert d.date is None and d.time is None
    assert d.location is None and d.address is None
    assert d.price is None
    assert d.latitude is None and d.longitude is None
    p = analysis.provenance
    assert p.date_stated is False
    assert p.time_stated is False
    assert p.location_stated is False
    assert p.address_stated is False
    assert p.price_stated is False
    assert p.coordinates_stated is False


async def test_event_without_date_does_not_invent_one():
    analysis = await _analyze(
        "Some concert festival gig with a great lineup and tickets available."
    )
    assert analysis.details.date is None
    assert analysis.provenance.date_stated is False
    assert analysis.resurfacing.type == TriggerType.MANUAL
    assert analysis.resurfacing.fire_at is None


async def test_mock_never_emits_coordinates():
    """The deterministic mock cannot geocode, so coordinates are always null and
    coordinates_stated always false - even for a well-specified place."""
    analysis = await _analyze(
        "Rooftop cafe on MG Road, Bangalore. Great coffee - a place to visit."
    )
    assert analysis.details.latitude is None
    assert analysis.details.longitude is None
    assert analysis.provenance.coordinates_stated is False


# ------------------------------------------------------------- confidence


async def test_confidence_high_for_rich_specific_content():
    analysis = await _analyze(
        "Amazing rooftop cafe and restaurant on MG Road, Bangalore. Great coffee and "
        "brunch, located near the beach - a must-visit place."
    )
    assert band_for(analysis.confidence) == ConfidenceBand.HIGH
    assert analysis.uncertainty_note is None


async def test_confidence_low_for_thin_content_sets_note():
    analysis = await _analyze("hmm ok")
    assert band_for(analysis.confidence) == ConfidenceBand.LOW
    assert analysis.uncertainty_note is not None


async def test_confidence_scores_intent_and_note_lifts_it():
    without = await _analyze("A nice article to read.")
    with_note = await _analyze("A nice article to read.", note="want to study this properly")
    assert with_note.confidence > without.confidence


# ------------------------------------------------- source vs inference split


async def test_content_and_intent_understanding_are_separable():
    """The A/B contract: content_understanding() carries only source facts +
    provenance; intent_understanding() carries only inferred fields."""
    analysis = await _analyze(
        "Concert live on 2026-09-14 at 8 pm. Tickets on sale - grab them."
    )

    content = analysis.content_understanding()
    intent = analysis.intent_understanding()

    assert set(content) == {"title", "summary", "entities", "details", "provenance"}
    assert set(intent) == {
        "why_saved",
        "intent_action",
        "confidence",
        "resurfacing",
        "suggested_actions",
    }
    # why_saved is an inference, phrased as such - never a bare source fact.
    assert intent["why_saved"].startswith("You probably saved this because")
    # the stated date lives on the content side with its provenance flag set.
    assert content["details"]["date"] == "2026-09-14"
    assert content["provenance"]["date_stated"] is True
